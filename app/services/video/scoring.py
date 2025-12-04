from typing import Any

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class ScoringService:
    def __init__(
        self,
        min_duration: int = settings.CLIP_MIN_DURATION_SECONDS,
        max_duration: int = settings.CLIP_MAX_DURATION_SECONDS,
        max_clips: int = settings.MAX_CLIPS_COUNT,
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_clips = max_clips

    def select_best_moments(
        self,
        segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Select up to 3 best moments (20-60sec each).

        Args:
            segments: List of transcription segments

        Returns:
            List of best moments with start and end times
        """
        if not segments:
            logger.warning("No segments provided for scoring")
            return []

        logger.info(
            f"Selecting best moments from {len(segments)} segments | "
            f"min_duration={self.min_duration}s | max_duration={self.max_duration}s",
        )

        if len(segments) == 0:
            return []

        segment_durations = [seg["end"] - seg["start"] for seg in segments]
        avg_duration = sum(segment_durations) / len(segment_durations) if segment_durations else 0
        logger.info(
            f"Segment statistics | count={len(segments)} | "
            f"avg_duration={avg_duration:.2f}s | "
            f"min_duration={min(segment_durations):.2f}s | "
            f"max_duration={max(segment_durations):.2f}s",
        )

        continuous_clips = self._find_continuous_speech_moments(segments=segments)
        
        logger.info(f"Found {len(continuous_clips)} continuous speech moments")

        continuous_clips.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        result = continuous_clips[: self.max_clips]
        logger.info(f"Selected {len(result)} best clips after sorting")
        return result

    def _find_continuous_speech_moments(
        self,
        segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Find continuous speech moments (without big pauses).

        Args:
            segments: List of transcription segments

        Returns:
            List of continuous moments with start, end, score
        """
        if not segments:
            return []

        clips = []
        i = 0
        max_pause = 3.0

        while i < len(segments):
            clip_start = segments[i]["start"]
            clip_segments = [segments[i]]
            j = i + 1

            while j < len(segments):
                prev_end = segments[j - 1]["end"]
                current_start = segments[j]["start"]
                pause = current_start - prev_end

                current_clip_duration = segments[j]["end"] - clip_start

                if pause <= max_pause and current_clip_duration <= self.max_duration:
                    clip_segments.append(segments[j])
                    j += 1
                else:
                    break

            clip_end = clip_segments[-1]["end"]
            clip_duration = clip_end - clip_start

            if clip_duration >= self.min_duration:
                combined_text = " ".join([s.get("text", "") for s in clip_segments])
                avg_score = sum([self._calculate_score(s) for s in clip_segments]) / len(clip_segments)
                clips.append({
                    "start": clip_start,
                    "end": clip_end,
                    "score": avg_score,
                    "text": combined_text,
                })

            i = j if j > i else i + 1

        return clips

    def _calculate_score(
        self,
        segment: dict[str, Any],
    ) -> float:
        """
        Calculate score for segment based on various factors.

        Args:
            segment: Segment dictionary

        Returns:
            Score value
        """
        text = segment.get("text", "").strip()
        text_length = len(text)

        duration = segment.get("end", 0) - segment.get("start", 0)

        base_score = text_length / max(duration, 1)

        has_question = "?" in text
        has_exclamation = "!" in text
        has_emphasis = has_question or has_exclamation

        if has_emphasis:
            base_score *= 1.5

        return base_score

