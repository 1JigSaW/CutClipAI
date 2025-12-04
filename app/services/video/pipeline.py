from pathlib import Path
from typing import Any, Optional

from app.core.logger import get_logger
from app.services.video.clipping import ClippingService
from app.services.video.scoring import ScoringService
from app.services.video.subtitles import SubtitlesService
from app.services.video.transcription import get_transcription_cache
from app.services.video.whisper import WhisperService
from app.utils.video.ffmpeg import cut_crop_and_burn_optimized
from app.utils.video.files import create_temp_dir

logger = get_logger(__name__)


class VideoPipeline:
    def __init__(
        self,
        whisper_service: Optional[WhisperService] = None,
        scoring_service: Optional[ScoringService] = None,
        clipping_service: Optional[ClippingService] = None,
        subtitles_service: Optional[SubtitlesService] = None,
    ):
        if whisper_service is None and subtitles_service is None:
            logger.info("Creating WhisperService with shared model for both services")
            shared_whisper_service = WhisperService()
            shared_model = shared_whisper_service.model
            self.whisper_service = shared_whisper_service
            logger.info("Creating SubtitlesService with shared Whisper model")
            self.subtitles_service = SubtitlesService(model=shared_model)
        else:
            self.whisper_service = whisper_service or WhisperService()
            if subtitles_service is None:
                logger.info("Reusing Whisper model for SubtitlesService")
                shared_model = self.whisper_service.model
                self.subtitles_service = SubtitlesService(model=shared_model)
            else:
                self.subtitles_service = subtitles_service

        logger.info("VideoPipeline initialized with shared Whisper model")

        self.scoring_service = scoring_service or ScoringService()
        self.clipping_service = clipping_service or ClippingService()

    def process(
        self,
        file_path: str,
    ) -> list[str]:
        """
        Run full pipeline: trim → whisper → scoring → clipping → subtitles.

        Args:
            file_path: Path to input video file

        Returns:
            List of paths to generated clip files
        """
        trimmed_path = self.clipping_service.trim_to_max_duration(
            file_path=file_path,
        )

        segments = self.whisper_service.extract_segments(
            video_path=trimmed_path,
        )

        logger.info(
            f"Extracted {len(segments)} segments from video | file_path={file_path}",
        )

        best_moments = self.scoring_service.select_best_moments(
            segments=segments,
        )

        logger.info(
            f"Selected {len(best_moments)} best moments for clipping",
        )

        clip_paths = []
        for moment in best_moments:
            clip_path = self.clipping_service.cut_clip(
                video_path=trimmed_path,
                start_time=moment["start"],
                end_time=moment["end"],
            )

            cropped_clip_path = self.clipping_service.crop_9_16(
                input_path=clip_path,
            )

            srt_path = self.subtitles_service.generate_srt(
                video_path=cropped_clip_path,
            )

            final_clip_path = self.subtitles_service.burn_subtitles(
                video_path=cropped_clip_path,
                srt_path=srt_path,
            )

            clip_paths.append(final_clip_path)

        return clip_paths

    def process_optimized(
        self,
        file_path: str,
    ) -> list[str]:
        """
        Optimized pipeline: single Whisper call + single FFmpeg pass per clip.
        4-5x faster than original pipeline.

        Args:
            file_path: Path to input video file

        Returns:
            List of paths to generated clip files
        """
        logger.info(
            f"Starting optimized video pipeline | file_path={file_path}",
        )

        trimmed_path = self.clipping_service.trim_to_max_duration(
            file_path=file_path,
        )

        logger.info(
            f"Video trimmed | trimmed_path={trimmed_path}",
        )

        transcription_result = self.whisper_service.transcribe_full(
            video_path=trimmed_path,
            use_cache=True,
        )

        logger.info(
            f"Full transcription completed | "
            f"segments_count={len(transcription_result.get('segments', []))}",
        )

        segments = []
        for segment in transcription_result.get("segments", []):
            segments.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                }
            )

        best_moments = self.scoring_service.select_best_moments(
            segments=segments,
        )

        logger.info(
            f"Selected {len(best_moments)} best moments for clipping",
        )

        clip_paths = []
        for idx, moment in enumerate(best_moments, 1):
            logger.info(
                f"Processing clip {idx}/{len(best_moments)} | "
                f"start={moment['start']:.2f}s | end={moment['end']:.2f}s",
            )

            output_dir = create_temp_dir()

            srt_path = self.subtitles_service.generate_srt(
                video_path=trimmed_path,
                source_video_path=trimmed_path,
                clip_start_time=moment["start"],
                clip_end_time=moment["end"],
            )

            clip_name = (
                f"final_clip_{idx}_"
                f"{moment['start']:.0f}_{moment['end']:.0f}.mp4"
            )
            final_clip_path = output_dir / clip_name

            cut_crop_and_burn_optimized(
                input_path=trimmed_path,
                output_path=str(final_clip_path),
                start_time=moment["start"],
                end_time=moment["end"],
                srt_path=srt_path,
            )

            logger.info(
                f"Clip {idx}/{len(best_moments)} processed | "
                f"path={final_clip_path}",
            )

            clip_paths.append(str(final_clip_path))

        logger.info(
            f"Optimized pipeline completed | clips_count={len(clip_paths)}",
        )

        cache = get_transcription_cache()
        cache.clear(video_path=trimmed_path)

        return clip_paths

