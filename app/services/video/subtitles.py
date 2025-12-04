from pathlib import Path
from typing import Any, Optional

import torch
import whisper

from app.core.config import settings
from app.core.logger import get_logger
from app.services.video.transcription import get_transcription_cache
from app.utils.video.ffmpeg import burn_subtitles as burn_subs
from app.utils.video.files import create_temp_dir

logger = get_logger(__name__)


class SubtitlesService:
    def __init__(
        self,
        model_name: str = settings.WHISPER_MODEL,
        model: Optional[Any] = None,
    ):
        self._detect_device()
        
        if model is not None:
            logger.debug(f"Using shared Whisper model for subtitles | model_name={model_name}")
            self.model = model
        else:
            logger.info(
                f"Loading Whisper model for subtitles | "
                f"model_name={model_name} | device={self.device}",
            )
            self.model = whisper.load_model(
                name=model_name,
                device=self.device,
            )
            logger.info(
                f"Whisper model loaded for subtitles | "
                f"model_name={model_name} | device={self.device}",
            )
        
        self.cache = get_transcription_cache()
    
    def _detect_device(self) -> None:
        if settings.FORCE_CPU:
            self.gpu_available = False
            self.device = "cpu"
            logger.debug(f"Forced CPU mode for subtitles | device={self.device}")
            return
        
        self.gpu_available = torch.cuda.is_available()
        
        if self.gpu_available:
            self.device = "cuda"
            logger.debug(f"Using GPU for subtitles | device={self.device}")
        else:
            self.device = "cpu"
            logger.debug(f"Using CPU for subtitles | device={self.device}")

    def generate_srt(
        self,
        video_path: str,
        source_video_path: Optional[str] = None,
        clip_start_time: Optional[float] = None,
        clip_end_time: Optional[float] = None,
    ) -> str:
        """
        Generate ASS subtitle file for video.
        Uses cached full transcription if available and filters by time range.

        Args:
            video_path: Path to video file (clip)
            source_video_path: Path to source video (for cache lookup)
            clip_start_time: Start time of clip in source video
            clip_end_time: End time of clip in source video

        Returns:
            Path to generated ASS file
        """
        logger.info(f"Starting subtitle generation for video | path={video_path}")

        use_cached = (
            source_video_path is not None
            and clip_start_time is not None
            and clip_end_time is not None
        )

        if use_cached:
            cached_result = self.cache.get(video_path=source_video_path)
            if cached_result:
                logger.info(
                    f"Using cached transcription for subtitles | "
                    f"source={source_video_path} | "
                    f"clip_range={clip_start_time:.2f}-{clip_end_time:.2f}s",
                )
                result = self._filter_segments_by_time(
                    transcription_result=cached_result,
                    start_time=clip_start_time,
                    end_time=clip_end_time,
                )
            else:
                logger.warning(
                    f"Cache miss for source video, transcribing clip | "
                    f"video_path={video_path}",
                )
                result = self.model.transcribe(
                    audio=video_path,
                    verbose=False,
                    word_timestamps=True,
                )
        else:
            logger.info(
                f"No cache info provided, transcribing clip directly | "
                f"video_path={video_path}",
            )
            result = self.model.transcribe(
                audio=video_path,
                verbose=False,
                word_timestamps=True,
            )

        segments_count = len(result.get("segments", []))
        logger.info(f"Transcribed video | segments_count={segments_count}")

        output_dir = create_temp_dir()
        ass_path = output_dir / f"{Path(video_path).stem}.ass"

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\n")
            f.write("Title: CutClipAI Subtitles\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n\n")
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,Arial,72,&H00FF69B4,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,2,10,10,480,1\n\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            for segment in result.get("segments", []):
                segment_start = segment["start"]
                segment_end = segment["end"]
                words = segment.get("words", [])

                if not words:
                    text = segment.get("text", "").strip()
                    if text:
                        start_time = self._format_ass_timestamp(seconds=segment_start)
                        end_time = self._format_ass_timestamp(seconds=segment_end)
                        f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
                    continue

                subtitle_lines = self._build_simple_lines(words=words)
                
                if not subtitle_lines:
                    logger.warning(
                        f"No subtitle lines generated for segment | "
                        f"start={segment_start:.2f}s | words_count={len(words)}",
                    )
                    continue
                
                logger.debug(
                    f"Generated {len(subtitle_lines)} subtitle lines for segment | "
                    f"start={segment_start:.2f}s",
                )
                
                for line_data in subtitle_lines:
                    start_time = self._format_ass_timestamp(seconds=line_data["start"])
                    end_time = self._format_ass_timestamp(seconds=line_data["end"])
                    line_text = line_data["text"]
                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{line_text}\n")

        logger.info(f"ASS subtitle file generated | path={ass_path}")

        return str(ass_path)

    def _filter_segments_by_time(
        self,
        transcription_result: dict[str, Any],
        start_time: float,
        end_time: float,
    ) -> dict[str, Any]:
        """
        Filter transcription segments by time range and adjust timestamps.

        Args:
            transcription_result: Full Whisper transcription result
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Filtered transcription result with adjusted timestamps
        """
        filtered_segments = []
        
        for segment in transcription_result.get("segments", []):
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", 0)
            
            if seg_end < start_time or seg_start > end_time:
                continue
            
            adjusted_segment = segment.copy()
            adjusted_segment["start"] = max(0, seg_start - start_time)
            adjusted_segment["end"] = max(0, seg_end - start_time)
            
            if "words" in segment:
                adjusted_words = []
                for word in segment["words"]:
                    word_start = word.get("start", 0)
                    word_end = word.get("end", 0)
                    
                    if word_end < start_time or word_start > end_time:
                        continue
                    
                    adjusted_word = word.copy()
                    adjusted_word["start"] = max(0, word_start - start_time)
                    adjusted_word["end"] = max(0, word_end - start_time)
                    adjusted_words.append(adjusted_word)
                
                adjusted_segment["words"] = adjusted_words
            
            filtered_segments.append(adjusted_segment)
        
        return {
            "segments": filtered_segments,
            "text": transcription_result.get("text", ""),
        }

    def _filter_early_words(
        self,
        words: list[dict[str, Any]],
        min_start_time: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Filter out words that start too early (remnants from previous segment).

        Args:
            words: List of word dictionaries with start, end, word
            min_start_time: Minimum start time in seconds to keep words

        Returns:
            Filtered list of words starting from first valid word
        """
        if not words:
            return []

        first_valid_idx = None
        for i, word_info in enumerate(words):
            word_start = word_info.get("start", 0)
            if word_start >= min_start_time:
                first_valid_idx = i
                break

        if first_valid_idx is None:
            return words

        return words[first_valid_idx:]

    def _build_simple_lines(
        self,
        words: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build list of subtitle lines without karaoke effect.
        Maximum 3 words per line.

        Args:
            words: List of word dictionaries with start, end, word

        Returns:
            List of dictionaries with start, end, and text for each line
        """
        if not words:
            return []

        lines_data = []
        current_line_words = []
        words_per_line = 3

        for word_info in words:
            word = word_info.get("word", "").strip()
            if not word:
                continue

            word_start = word_info.get("start", 0)
            word_end = word_info.get("end", 0)

            if len(current_line_words) >= words_per_line:
                line_start = current_line_words[0]["start"]
                line_end = current_line_words[-1]["end"]
                line_text = " ".join([w["word"] for w in current_line_words])
                
                lines_data.append({
                    "start": line_start,
                    "end": line_end,
                    "text": line_text,
                })
                current_line_words = []

            current_line_words.append({
                "word": word,
                "start": word_start,
                "end": word_end,
            })

        if current_line_words:
            line_start = current_line_words[0]["start"]
            line_end = current_line_words[-1]["end"]
            line_text = " ".join([w["word"] for w in current_line_words])
            
            lines_data.append({
                "start": line_start,
                "end": line_end,
                "text": line_text,
            })

        return lines_data

    def _create_line_data(
        self,
        line_words: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create subtitle line data with karaoke text.

        Args:
            line_words: List of word dictionaries for this line

        Returns:
            Dictionary with start, end, and text
        """
        if not line_words:
            return {"start": 0, "end": 0, "text": ""}

        line_start = line_words[0]["start"]
        line_end = line_words[-1]["end"]
        line_text = self._build_line_karaoke(
            line_words=line_words,
            line_start=line_start,
        )

        return {
            "start": line_start,
            "end": line_end,
            "text": line_text,
        }

    def _build_line_karaoke(
        self,
        line_words: list[dict[str, Any]],
        line_start: float,
    ) -> str:
        """
        Build karaoke text for a single line.

        Args:
            line_words: List of word dictionaries for this line
            line_start: Start time of the first word in this line

        Returns:
            ASS formatted text for the line
        """
        if not line_words:
            return ""

        karaoke_parts = []

        for i, word_data in enumerate(line_words):
            word = word_data["word"]
            word_start = word_data["start"]
            word_end = word_data["end"]
            duration_ms = max(10, int((word_end - word_start) * 1000))

            if i == 0:
                pause_ms = max(0, int((word_start - line_start) * 1000))
                if pause_ms > 0:
                    karaoke_parts.append(f"{{\\k{pause_ms}}}{{\\kf{duration_ms}}}{word}")
                else:
                    karaoke_parts.append(f"{{\\kf{duration_ms}}}{word}")
            else:
                prev_word_end = line_words[i - 1]["end"]
                pause_ms = max(0, int((word_start - prev_word_end) * 1000))

                if pause_ms > 0:
                    karaoke_parts.append(f" {{\\k{pause_ms}}}{{\\kf{duration_ms}}}{word}")
                else:
                    karaoke_parts.append(f" {{\\kf{duration_ms}}}{word}")

        return "".join(karaoke_parts)

    def burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
    ) -> str:
        """
        Burn subtitles into video.

        Args:
            video_path: Path to video file
            srt_path: Path to ASS subtitle file

        Returns:
            Path to video file with burned subtitles
        """
        output_dir = create_temp_dir()
        output_path = output_dir / f"final_{Path(video_path).name}"

        burn_subs(
            video_path=video_path,
            srt_path=srt_path,
            output_path=str(output_path),
        )

        return str(output_path)

    @staticmethod
    def _format_ass_timestamp(
        seconds: float,
    ) -> str:
        """
        Format seconds to ASS timestamp format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string (H:MM:SS.cc)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)

        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    @staticmethod
    def _format_timestamp(
        seconds: float,
    ) -> str:
        """
        Format seconds to SRT timestamp format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

