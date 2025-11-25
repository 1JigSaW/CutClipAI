from typing import Any

from app.core.config import settings


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
            return []

        valid_moments = []
        for i, segment in enumerate(segments):
            start = segment["start"]
            end = segment["end"]
            duration = end - start

            if self.min_duration <= duration <= self.max_duration:
                valid_moments.append(
                    {
                        "start": start,
                        "end": end,
                        "score": self._calculate_score(segment=segment),
                        "text": segment.get("text", ""),
                    }
                )

        valid_moments.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return valid_moments[: self.max_clips]

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

