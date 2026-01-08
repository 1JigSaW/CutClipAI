"""
AssemblyAI-based subtitle generation service.
Uses word-level timing from AssemblyAI for precise subtitles.
Based on supoclip/backend structure.
"""

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


class AssemblyAISubtitlesService:
    """
    Service for generating subtitles using AssemblyAI word-level timing data.
    Provides precise subtitle synchronization.
    """

    def __init__(self):
        logger.info("AssemblyAI subtitles service initialized")

    def generate_srt(
        self,
        video_path: str | Path,
        clip_start_time: float,
        clip_end_time: float,
    ) -> str:
        """
        Generate ASS subtitle file from AssemblyAI cached data with positioning at 75% height.
        ASS format is used instead of SRT to support precise positioning.

        Args:
            video_path: Path to source video file
            clip_start_time: Start time of clip in source video (seconds)
            clip_end_time: End time of clip in source video (seconds)

        Returns:
            Path to generated ASS file
        """
        return self.generate_srt_from_assemblyai(
            video_path=video_path,
            clip_start_time=clip_start_time,
            clip_end_time=clip_end_time,
        )

    def generate_srt_from_assemblyai(
        self,
        video_path: str | Path,
        clip_start_time: float,
        clip_end_time: float,
    ) -> str:
        """
        Generate ASS subtitle file from AssemblyAI cached data with positioning at 75% height.
        ASS format is used instead of SRT to support precise positioning.

        Args:
            video_path: Path to source video file
            clip_start_time: Start time of clip in source video (seconds)
            clip_end_time: End time of clip in source video (seconds)

        Returns:
            Path to generated ASS file
        """
        if isinstance(video_path, str):
            video_path = Path(video_path)

        cache_path = video_path.with_suffix('.assemblyai_cache.json')

        if not cache_path.exists():
            logger.warning(
                f"AssemblyAI cache not found | cache_path={cache_path}. "
                f"Subtitle generation will be skipped."
            )
            return None

        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)

            words = cached_data.get('words', [])
            if not words:
                logger.warning("No word-level data in AssemblyAI cache")
                return None
            
            logger.info(
                f"🔍 Searching for words | "
                f"clip_range={clip_start_time:.1f}s-{clip_end_time:.1f}s | "
                f"total_words={len(words)} | "
                f"cache={cache_path}"
            )
            
            if words:
                first_word = words[0]
                last_word = words[-1]
                logger.info(
                    f"📊 Cache time range | "
                    f"first={first_word.get('start', 0):.2f}s ('{first_word.get('text', '')}') | "
                    f"last={last_word.get('end', 0):.2f}s ('{last_word.get('text', '')}')"
                )

            relevant_words = []
            for w in words:
                word_start = w.get('start', 0)
                word_end = w.get('end', word_start)
                if word_start < clip_end_time and word_end > clip_start_time:
                    relevant_words.append(w)

            if not relevant_words:
                logger.error(
                    f"❌ NO WORDS FOUND! | "
                    f"clip={clip_start_time:.1f}s-{clip_end_time:.1f}s | "
                    f"cache_words={len(words)} | "
                    f"PROCESSING WITHOUT SUBTITLES"
                )
                return None
            
            logger.info(
                f"✅ Found {len(relevant_words)} words for subtitles | "
                f"clip={clip_start_time:.1f}s-{clip_end_time:.1f}s"
            )

            subtitle_entries = []
            current_words = []
            current_start = None
            max_chars_per_line = 42
            max_duration_sec = 3.0

            for word in relevant_words:
                word_start = word.get('start', 0)
                word_end = word.get('end', 0)
                word_text = word.get('text', '')

                word_start_rel = max(0, word_start - clip_start_time)
                word_end_rel = max(0, word_end - clip_start_time)

                if current_start is None:
                    current_start = word_start_rel

                current_words.append(word_text)

                should_finish = False

                char_count = sum(len(w) for w in current_words) + len(current_words) - 1
                duration = word_end_rel - current_start

                if char_count >= max_chars_per_line:
                    should_finish = True
                elif duration >= max_duration_sec:
                    should_finish = True

                if should_finish:
                    min_duration_sec = 0.5
                    actual_end = max(word_end_rel, current_start + min_duration_sec)
                    subtitle_entries.append({
                        'start_ms': current_start * 1000,
                        'end_ms': actual_end * 1000,
                        'text': ' '.join(current_words)
                    })
                    current_words = []
                    current_start = None

            if current_words and current_start is not None:
                last_word = relevant_words[-1]
                last_word_end_rel = last_word.get('end', clip_end_time) - clip_start_time
                min_duration_sec = 0.5
                actual_end = max(last_word_end_rel, current_start + min_duration_sec)
                subtitle_entries.append({
                    'start_ms': current_start * 1000,
                    'end_ms': actual_end * 1000,
                    'text': ' '.join(current_words)
                })

            output_dir = Path(video_path).parent
            ass_path = output_dir / f"subtitles_{clip_start_time:.0f}_{clip_end_time:.0f}.ass"

            if not subtitle_entries:
                logger.warning(
                    f"No subtitle entries generated! | "
                    f"words={len(relevant_words)} | "
                    f"clip_start={clip_start_time}s | clip_end={clip_end_time}s"
                )
                return None
            
            ass_content = self._create_ass_file_with_positioning(subtitle_entries)
            
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            
            # Verify content was written
            written_content = ass_path.read_text(encoding='utf-8')
            dialogue_count = written_content.count('Dialogue:')
            if dialogue_count == 0:
                logger.error(
                    f"ASS file written but contains no Dialogue entries! | "
                    f"file_size={ass_path.stat().st_size} | "
                    f"content_preview={written_content[:500]}"
                )

            # Verify file was written correctly
            written_size = ass_path.stat().st_size
            logger.info(
                f"Generated ASS from AssemblyAI | "
                f"ass_path={ass_path} | words={len(relevant_words)} | "
                f"subtitles={len(subtitle_entries)} | file_size={written_size} bytes"
            )
            
            # Log first few lines for debugging
            if subtitle_entries:
                logger.debug(
                    f"ASS file preview | "
                    f"first_subtitle={subtitle_entries[0].get('text', '')[:50]}... | "
                    f"first_time={self._ms_to_ass_time(subtitle_entries[0]['start_ms'])}"
                )

            return str(ass_path)

        except Exception as e:
            logger.error(
                f"Failed to generate subtitles from AssemblyAI | error={e}",
                exc_info=True
            )
            return None

    def _create_empty_ass_file(self) -> str:
        """Create empty ASS file with default styling."""
        return self._create_ass_file_with_positioning([])

    def _create_ass_file_with_positioning(
        self,
        subtitle_entries: List[dict],
    ) -> str:
        """
        Create ASS subtitle file with positioning at 75% height (lower-middle).
        Uses Alignment=2 (bottom center) with MarginV to position subtitles.
        For 1920px height video: 75% from top = 1440px, MarginV = 480px (25% from bottom).
        
        Args:
            subtitle_entries: List of dicts with 'start_ms', 'end_ms', 'text'
        
        Returns:
            ASS file content as string
        """
        video_height = 1920
        
        margin_v = int(video_height * 0.25)
        
        font_size = 36
        outline = 2
        shadow = 0
        alignment = 2
        
        ass_lines = [
            "[Script Info]",
            "Title: AssemblyAI Subtitles",
            "ScriptType: v4.00+",
            "Collisions: Normal",
            "PlayDepth: 0",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},{shadow},{alignment},10,10,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        
        for entry in subtitle_entries:
            start_ms = entry['start_ms']
            end_ms = entry['end_ms']
            
            # CRITICAL: Ensure end time is always greater than start time
            # FFmpeg/libass will not display subtitles with zero duration
            if end_ms <= start_ms:
                end_ms = start_ms + 500  # Add minimum 500ms duration
            
            start_time = self._ms_to_ass_time(start_ms)
            end_time = self._ms_to_ass_time(end_ms)
            text = self._escape_ass_text(entry['text'])
            
            ass_lines.append(
                f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
            )
        
        return '\n'.join(ass_lines)

    def _escape_ass_text(self, text: str) -> str:
        """
        Escape special characters in ASS subtitle text.
        ASS format requires escaping: \\, {, }, &, N, n, H, h
        """
        escaped = text.replace('\\', '\\\\')
        escaped = escaped.replace('{', '\\{')
        escaped = escaped.replace('}', '\\}')
        escaped = escaped.replace('&', '\\&')
        escaped = escaped.replace('\n', '\\N')
        return escaped

    def _ms_to_ass_time(self, milliseconds: float) -> str:
        """Convert milliseconds to ASS time format (H:MM:SS.cc)."""
        milliseconds = int(milliseconds)
        total_seconds = milliseconds // 1000
        centiseconds = (milliseconds % 1000) // 10
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

