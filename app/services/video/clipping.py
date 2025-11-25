from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.utils.video.files import create_temp_dir
from app.utils.video.ffmpeg import (
    crop_9_16,
    cut_clip,
    trim_video,
)


class ClippingService:
    def __init__(
        self,
        max_duration: int = settings.VIDEO_MAX_DURATION_SECONDS,
    ):
        self.max_duration = max_duration

    def trim_to_max_duration(
        self,
        file_path: str,
    ) -> str:
        """
        Trim video to maximum duration (30 minutes).

        Args:
            file_path: Path to input video file

        Returns:
            Path to trimmed video file
        """
        output_dir = create_temp_dir()
        output_path = output_dir / f"trimmed_{Path(file_path).name}"

        trim_video(
            input_path=file_path,
            output_path=str(output_path),
            max_duration=self.max_duration,
        )

        return str(output_path)

    def cut_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
    ) -> str:
        """
        Cut clip from video using ffmpeg.

        Args:
            video_path: Path to source video
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Path to generated clip file
        """
        output_dir = create_temp_dir()
        clip_name = f"clip_{start_time:.0f}_{end_time:.0f}_{Path(video_path).stem}.mp4"
        output_path = output_dir / clip_name

        cut_clip(
            input_path=video_path,
            output_path=str(output_path),
            start_time=start_time,
            end_time=end_time,
        )

        return str(output_path)

    def crop_9_16(
        self,
        input_path: str,
    ) -> str:
        """
        Crop video to 9:16 aspect ratio if needed.

        Args:
            input_path: Path to input video

        Returns:
            Path to cropped video file
        """
        output_dir = create_temp_dir()
        output_path = output_dir / f"cropped_{Path(input_path).name}"

        crop_9_16(
            input_path=input_path,
            output_path=str(output_path),
        )

        return str(output_path)

