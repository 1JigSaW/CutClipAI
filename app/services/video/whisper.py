from pathlib import Path
from typing import Any

import whisper

from app.core.config import settings


class WhisperService:
    def __init__(
        self,
        model_name: str = settings.WHISPER_MODEL,
    ):
        self.model = whisper.load_model(name=model_name)

    def extract_segments(
        self,
        video_path: str,
    ) -> list[dict[str, Any]]:
        """
        Extract transcription segments from video.

        Args:
            video_path: Path to video file

        Returns:
            List of segments with start, end, and text
        """
        result = self.model.transcribe(
            video=video_path,
            verbose=False,
        )

        segments = []
        for segment in result.get("segments", []):
            segments.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                }
            )

        return segments

