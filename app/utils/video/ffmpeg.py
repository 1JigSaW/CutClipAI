import subprocess
from pathlib import Path

from app.core.config import settings


def trim_video(
    input_path: str,
    output_path: str,
    max_duration: int,
) -> None:
    """
    Trim video to maximum duration.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        max_duration: Maximum duration in seconds
    """
    subprocess.run(
        [
            settings.FFMPEG_PATH,
            "-i",
            input_path,
            "-t",
            str(max_duration),
            "-c",
            "copy",
            "-y",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def cut_clip(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
) -> None:
    """
    Cut clip from video.

    Args:
        input_path: Path to input video
        output_path: Path to output clip
        start_time: Start time in seconds
        end_time: End time in seconds
    """
    duration = end_time - start_time

    subprocess.run(
        [
            settings.FFMPEG_PATH,
            "-i",
            input_path,
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-c",
            "copy",
            "-y",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def crop_9_16(
    input_path: str,
    output_path: str,
) -> None:
    """
    Crop video to 9:16 aspect ratio.

    Args:
        input_path: Path to input video
        output_path: Path to output video
    """
    subprocess.run(
        [
            settings.FFMPEG_PATH,
            "-i",
            input_path,
            "-vf",
            "crop=ih*9/16:ih,scale=1080:1920",
            "-y",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
) -> None:
    """
    Burn subtitles into video.

    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitle file
        output_path: Path to output video with subtitles
    """
    subprocess.run(
        [
            settings.FFMPEG_PATH,
            "-i",
            video_path,
            "-vf",
            f"subtitles={srt_path}",
            "-c:a",
            "copy",
            "-y",
            output_path,
        ],
        check=True,
        capture_output=True,
    )

