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


def _get_ffmpeg_preset() -> str:
    """
    Get FFmpeg preset for encoding.
    Uses configured preset from settings.

    Returns:
        Preset name
    """
    return settings.FFMPEG_PRESET


def _get_ffmpeg_quality() -> int:
    """
    Get FFmpeg quality setting (CQ value).
    Lower value = better quality, higher file size.
    Range: 0-51 (23 is good balance).

    Returns:
        Quality value (CQ)
    """
    return settings.FFMPEG_QUALITY


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


def _build_ffmpeg_base_cmd(
    input_path: str,
    output_path: str,
    use_gpu: bool = True,
) -> list[str]:
    """
    Build base FFmpeg command with GPU acceleration.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        use_gpu: Whether to use GPU acceleration

    Returns:
        Base FFmpeg command list
    """
    cmd = [
        settings.FFMPEG_PATH,
        "-hwaccel",
        "auto",
    ]
    
    if use_gpu and _get_gpu_encoding_available():
        cmd.extend(["-hwaccel_output_format", "cuda"])
    
    cmd.extend(["-i", input_path])
    
    return cmd


def _run_ffmpeg(
    cmd: list[str],
    operation: str = "video processing",
) -> None:
    """
    Run FFmpeg command with error handling.

    Args:
        cmd: FFmpeg command list
        operation: Description of operation for logging
    """
    logger.debug(
        f"Running FFmpeg {operation} | "
        f"gpu_available={_get_gpu_encoding_available()}",
    )
    
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
    )


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
    cmd = _build_ffmpeg_base_cmd(
        input_path=input_path,
        output_path=output_path,
    )
    cmd.extend([
            "-t",
            str(max_duration),
            "-c",
            "copy",
        "-avoid_negative_ts",
        "make_zero",
            "-y",
            output_path,
    ])
    
    _run_ffmpeg(
        cmd=cmd,
        operation="trim",
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

    cmd = _build_ffmpeg_base_cmd(
        input_path=input_path,
        output_path=output_path,
    )
    cmd.insert(-2, "-ss")
    cmd.insert(-2, str(start_time))
    cmd.extend([
            "-t",
            str(duration),
            "-c",
            "copy",
            "-y",
            output_path,
    ])
    
    _run_ffmpeg(
        cmd=cmd,
        operation=f"cut clip (start={start_time}s, end={end_time}s)",
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
    preset = _get_ffmpeg_preset()
    quality = _get_ffmpeg_quality()
    
    cmd = _build_ffmpeg_base_cmd(
        input_path=input_path,
        output_path=output_path,
    )
    # Smart crop: only crop if video is wider than 9:16
    # If video is already 9:16 or narrower, don't crop (use full width)
    # Formula: crop=min(iw, ih*9/16):ih:(iw-min(iw,ih*9/16))/2:0
    cmd.extend([
            "-vf",
        f"crop=min(iw,ih*9/16):ih:(iw-min(iw,ih*9/16))/2:0,{scale_filter}",
        "-c:v",
        video_codec,
        "-preset",
        preset,
            "-y",
            output_path,
    ])
    
    if _get_gpu_encoding_available():
        cmd.extend(["-rc", "vbr", "-cq", str(quality), "-b:v", "0"])
    
    _run_ffmpeg(
        cmd=cmd,
        operation=f"crop to 9:16 (codec={video_codec})",
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
    
    cmd = _build_ffmpeg_base_cmd(
        input_path=video_path,
        output_path=output_path,
    )
    preset = _get_ffmpeg_preset()
    quality = _get_ffmpeg_quality()
    
    cmd.extend([
            "-vf",
            f"subtitles={srt_path}",
        "-c:v",
        video_codec,
        "-preset",
        preset,
            "-c:a",
            "copy",
            "-y",
            output_path,
    ])
    
    if _get_gpu_encoding_available():
        cmd.extend(["-rc", "vbr", "-cq", str(quality), "-b:v", "0"])
    
    _run_ffmpeg(
        cmd=cmd,
        operation=f"burn subtitles (codec={video_codec})",
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
    
    video_codec = _get_video_codec()
    
    # Smart crop to 9:16 with proper aspect ratio preservation
    # Step 1: Crop width from center if video is wider than 9:16
    # Step 2: Scale to 1080x1920 maintaining aspect ratio (may be smaller)
    # Step 3: Pad to exact 1080x1920 with black bars centered
    # This prevents stretching by using scale with force_original_aspect_ratio=decrease and pad
    # pad syntax: pad=width:height:x:y:color
    # For centering: use eval filter to calculate positions, or use simpler approach
    # Using scale with force_original_aspect_ratio=decrease then pad with -1 for auto-center
    # If -1 doesn't work, we'll use explicit calculations
    video_filter = (
        f"crop=min(iw,ih*9/16):ih:(iw-min(iw,ih*9/16))/2:0,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:-1:-1:black,"
        f"subtitles={srt_path}"
    )
    
    cmd = _build_ffmpeg_base_cmd(
        input_path=input_path,
        output_path=output_path,
        use_gpu=False,
    )
    cmd.insert(-2, "-ss")
    cmd.insert(-2, str(start_time))
    preset = _get_ffmpeg_preset()
    quality = _get_ffmpeg_quality()
    
    cmd.extend([
            "-t",
            str(duration),
            "-vf",
            video_filter,
        "-c:v",
        video_codec,
        "-preset",
        preset,
            "-c:a",
            "copy",
            "-y",
            output_path,
    ])
    
    if _get_gpu_encoding_available():
        cmd.extend(["-rc", "vbr", "-cq", str(quality), "-b:v", "0"])
    
    _run_ffmpeg(
        cmd=cmd,
        operation=f"cut, crop and burn (codec={video_codec}, start={start_time}s, end={end_time}s)",
    )

