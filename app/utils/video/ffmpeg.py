import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _check_gpu_encoding_available() -> bool:
    """
    Check if GPU encoding (NVENC) is available in FFmpeg.

    Returns:
        True if GPU encoding is available, False otherwise
    """
    if not settings.USE_GPU_ENCODING:
        return False
    
    try:
        result = subprocess.run(
            [
                settings.FFMPEG_PATH,
                "-hide_banner",
                "-encoders",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if "h264_nvenc" in result.stdout or "hevc_nvenc" in result.stdout:
            logger.info("GPU encoding (NVENC) is available in FFmpeg")
            return True
        else:
            logger.debug("GPU encoding (NVENC) is not available in FFmpeg")
            return False
    except Exception as e:
        logger.warning(f"Failed to check GPU encoding availability: {e}")
        return False


_GPU_ENCODING_AVAILABLE = None


def _get_gpu_encoding_available() -> bool:
    """
    Get cached GPU encoding availability status.

    Returns:
        True if GPU encoding is available, False otherwise
    """
    global _GPU_ENCODING_AVAILABLE
    if _GPU_ENCODING_AVAILABLE is None:
        _GPU_ENCODING_AVAILABLE = _check_gpu_encoding_available()
    return _GPU_ENCODING_AVAILABLE


def _get_video_codec() -> str:
    """
    Get video codec for encoding.
    Uses GPU encoding if available, otherwise uses CPU.

    Returns:
        Video codec name
    """
    if _get_gpu_encoding_available():
        return "h264_nvenc"
    return "libx264"


def _get_scale_filter() -> str:
    """
    Get scale filter for video processing.
    Uses GPU scaling if available, otherwise uses CPU.

    Returns:
        Scale filter string
    """
    if _get_gpu_encoding_available():
        return "scale_npp=1080:1920"
    return "scale=1080:1920"


def trim_video(
    input_path: str,
    output_path: str,
    max_duration: int,
) -> None:
    """
    Trim video to maximum duration.
    Uses GPU hardware acceleration when available.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        max_duration: Maximum duration in seconds
    """
    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
        "-i",
        input_path,
        "-t",
        str(max_duration),
        "-c",
        "copy",
        "-y",
        output_path,
    ]
    
    logger.debug(
        f"Trimming video with GPU acceleration | "
        f"gpu_available={_get_gpu_encoding_available()}",
    )
    
    subprocess.run(
        cmd,
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
    Uses GPU hardware acceleration when available.

    Args:
        input_path: Path to input video
        output_path: Path to output clip
        start_time: Start time in seconds
        end_time: End time in seconds
    """
    duration = end_time - start_time

    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
        "-ss",
        str(start_time),
        "-i",
        input_path,
        "-t",
        str(duration),
        "-c",
        "copy",
        "-y",
        output_path,
    ]
    
    logger.debug(
        f"Cutting clip with GPU acceleration | "
        f"gpu_available={_get_gpu_encoding_available()} | "
        f"start={start_time}s | end={end_time}s",
    )

    subprocess.run(
        cmd,
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
    scale_filter = _get_scale_filter()
    video_codec = _get_video_codec()
    
    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
        "-i",
        input_path,
        "-vf",
        f"crop=ih*9/16:ih,{scale_filter}",
        "-c:v",
        video_codec,
        "-preset",
        "fast",
        "-y",
        output_path,
    ]
    
    if _get_gpu_encoding_available():
        cmd.extend(["-rc", "vbr", "-cq", "23"])
    
    logger.debug(
        f"Cropping video with GPU acceleration | "
        f"gpu_available={_get_gpu_encoding_available()} | "
        f"codec={video_codec}",
    )
    
    subprocess.run(
        cmd,
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
        srt_path: Path to ASS subtitle file
        output_path: Path to output video with subtitles
    """
    video_codec = _get_video_codec()
    
    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
        "-i",
        video_path,
        "-vf",
        f"subtitles={srt_path}",
        "-c:v",
        video_codec,
        "-preset",
        "fast",
        "-c:a",
        "copy",
        "-y",
        output_path,
    ]
    
    if _get_gpu_encoding_available():
        cmd.extend(["-rc", "vbr", "-cq", "23"])
    
    logger.debug(
        f"Burning subtitles with GPU acceleration | "
        f"gpu_available={_get_gpu_encoding_available()} | "
        f"codec={video_codec}",
    )
    
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
    )


def cut_crop_and_burn_optimized(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    srt_path: str,
) -> None:
    """
    Optimized single-pass operation: cut clip, crop to 9:16, and burn subtitles.
    Uses GPU acceleration when available for 3-5x faster processing.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        start_time: Start time in seconds
        end_time: End time in seconds
        srt_path: Path to ASS subtitle file
    """
    duration = end_time - start_time
    
    scale_filter = _get_scale_filter()
    video_codec = _get_video_codec()
    video_filter = f"crop=ih*9/16:ih,{scale_filter},subtitles={srt_path}"
    
    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
        "-ss",
        str(start_time),
        "-i",
        input_path,
        "-t",
        str(duration),
        "-vf",
        video_filter,
        "-c:v",
        video_codec,
        "-preset",
        "fast",
        "-c:a",
        "copy",
        "-y",
        output_path,
    ]
    
    if _get_gpu_encoding_available():
        cmd.insert(2, "-hwaccel_output_format")
        cmd.insert(3, "cuda")
        cmd.extend(["-rc", "vbr", "-cq", "23", "-b:v", "0"])
    
    logger.info(
        f"Processing clip with GPU acceleration | "
        f"gpu_available={_get_gpu_encoding_available()} | "
        f"codec={video_codec} | start={start_time}s | end={end_time}s",
    )
    
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
    )

