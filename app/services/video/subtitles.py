from pathlib import Path
from typing import Any

import whisper

from app.core.config import settings
from app.utils.video.ffmpeg import burn_subtitles as burn_subs
from app.utils.video.files import create_temp_dir


class SubtitlesService:
    def __init__(
        self,
        model_name: str = settings.WHISPER_MODEL,
    ):
        self.model = whisper.load_model(name=model_name)

    def generate_srt(
        self,
        video_path: str,
    ) -> str:
        """
        Generate SRT subtitle file for video.

        Args:
            video_path: Path to video file

        Returns:
            Path to generated SRT file
        """
        result = self.model.transcribe(
            video=video_path,
            verbose=False,
        )

        output_dir = create_temp_dir()
        srt_path = output_dir / f"{Path(video_path).stem}.srt"

        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, segment in enumerate(result.get("segments", []), start=1):
                start_time = self._format_timestamp(seconds=segment["start"])
                end_time = self._format_timestamp(seconds=segment["end"])
                text = segment["text"].strip()

                f.write(f"{idx}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

        return str(srt_path)

    def burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
    ) -> str:
        """
        Burn subtitles into video.

        Args:
            video_path: Path to video file
            srt_path: Path to SRT subtitle file

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

