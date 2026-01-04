import shlex
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
    Returns appropriate preset based on codec (GPU vs CPU).

    Returns:
        Preset name
    """
    configured_preset = settings.FFMPEG_PRESET
    
    if _get_gpu_encoding_available() and _get_video_codec() == "h264_nvenc":
        if configured_preset in ["p1", "p2", "p3", "p4", "p5", "p6", "p7"]:
            return configured_preset
        return "p1"
    else:
        if configured_preset in ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"]:
            return configured_preset
        return "veryfast"


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
    
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown error"
        full_cmd = ' '.join(cmd)
        logger.error(
            f"FFmpeg command failed | returncode={result.returncode} | "
            f"operation={operation} | "
            f"full_cmd={full_cmd} | "
            f"stderr={error_msg}"
        )
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    else:
        if result.stderr:
            stderr_lower = result.stderr.lower()
            if 'subtitle' in stderr_lower or 'ass' in stderr_lower or 'libass' in stderr_lower:
                logger.warning(
                    f"FFmpeg stderr contains subtitle-related messages | "
                    f"operation={operation} | "
                    f"stderr={result.stderr[:1000]}"
                )
            if 'error' in stderr_lower or 'warning' in stderr_lower:
                logger.warning(
                    f"FFmpeg stderr contains errors/warnings | "
                    f"operation={operation} | "
                    f"stderr={result.stderr[:1000]}"
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
    # Robust crop to 9:16: Scale to cover target, then crop center
    # This prevents stretching and always fills the 1080x1920 frame
    cmd.extend([
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
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
    Supports ASS format with positioning at 75% height (lower-middle).

    Args:
        video_path: Path to input video
        srt_path: Path to ASS subtitle file (ASS format for positioning support)
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
    srt_path: str | None,
) -> None:
    """
    Optimized single-pass operation: cut clip, crop to 9:16, and burn subtitles.
    Uses GPU acceleration when available for 3-5x faster processing.
    Subtitles are positioned at 75% height (lower-middle) via ASS format.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        start_time: Start time in seconds
        end_time: End time in seconds
        srt_path: Path to ASS subtitle file (ASS format supports positioning)
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
    # Handle None or empty string for srt_path
    use_subtitles = False
    srt_path_str = ""
    
    if srt_path:
        srt_path_str = str(srt_path)
        srt_path_obj = Path(srt_path_str)
        # Check if subtitle file exists and is not empty
        if srt_path_obj.exists():
            file_size = srt_path_obj.stat().st_size
            if file_size > 0:
                use_subtitles = True
            else:
                logger.warning(f"Subtitle file is empty: {srt_path_str}, processing without subtitles")
        else:
            logger.warning(f"Subtitle file not found: {srt_path_str}, processing without subtitles")
    else:
        logger.debug("No subtitle path provided, processing without subtitles")
    
    # Robust 9:16 transformation:
    # 1. Scale to cover 1080x1920 (no stretching)
    # 2. Crop center 1080x1920
    # 3. Force square pixels
    base_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setsar=1"
    )
    
    if use_subtitles:
        # For FFmpeg subtitles filter, we need to escape the path properly
        # The filter syntax is: subtitles=filename
        # On macOS, paths contain colons which need special handling
        # Use absolute path and escape colons with backslash
        abs_path = str(srt_path_obj.resolve())
        
        # FFmpeg subtitles filter requires escaping special characters in paths
        # CRITICAL: On macOS, paths contain colons (:) which MUST be escaped as \:
        # The escape sequence \: tells FFmpeg that : is part of the path, not a filter separator
        # Escape order: first backslashes, then colons, then brackets
        escaped_path = abs_path
        
        # Step 1: Escape backslashes first (so we don't double-escape)
        if '\\' in escaped_path:
            escaped_path = escaped_path.replace('\\', '\\\\')
        
        # Step 2: Escape colons (CRITICAL for macOS paths like /Users/jigsaw/...)
        if ':' in escaped_path:
            escaped_path = escaped_path.replace(':', '\\:')
        
        # Step 3: Escape brackets
        if '[' in escaped_path:
            escaped_path = escaped_path.replace('[', '\\[')
        if ']' in escaped_path:
            escaped_path = escaped_path.replace(']', '\\]')
        
        # Build filter with subtitles
        # CRITICAL: Use 'subtitles' filter (not 'ass') - it's more reliable and handles ASS format
        # FFmpeg subtitles filter auto-detects ASS format and works better
        # Syntax: subtitles=filename (path must be escaped)
        video_filter = f"{base_filter},subtitles={escaped_path}"
        
        # Log the filter for debugging
        logger.info(
            f"Subtitle filter construction | "
            f"original_path={abs_path} | "
            f"escaped_path={escaped_path} | "
            f"path_exists={srt_path_obj.exists()} | "
            f"filter_snippet=subtitles={escaped_path[:80]}..."
        )
        
        # Verify file exists and is readable
        if not srt_path_obj.exists():
            logger.error(
                f"ASS file does not exist! | path={abs_path} | "
                f"Subtitles will not be applied!"
            )
        elif not srt_path_obj.is_file():
            logger.error(
                f"ASS path is not a file! | path={abs_path} | "
                f"Subtitles will not be applied!"
            )
        
        file_size = srt_path_obj.stat().st_size
        
        # Log the actual FFmpeg command that will be used
        # Show both original and escaped paths for debugging
        logger.info(
            f"Adding subtitles to video filter | "
            f"original_path={abs_path} | "
            f"escaped_path={escaped_path} | "
            f"file_size={file_size} bytes | "
            f"colons_in_path={abs_path.count(':')} | "
            f"colons_escaped={escaped_path.count('\\\\:')}"
        )
        
        # Verify file is readable and has valid ASS content
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                logger.debug(
                    f"ASS file validation | "
                    f"total_lines={len(lines)} | "
                    f"first_line={lines[0] if lines else 'empty'} | "
                    f"has_events={any('[Events]' in line for line in lines)} | "
                    f"has_styles={any('[V4+ Styles]' in line or '[V4 Styles]' in line for line in lines)}"
                )
                
                # Count dialogue entries
                dialogue_count = sum(1 for line in lines if line.startswith('Dialogue:'))
                logger.info(
                    f"ASS file contains {dialogue_count} subtitle entries | "
                    f"file_size={file_size} bytes"
                )
                
                if dialogue_count == 0:
                    logger.warning(
                        f"ASS file has no dialogue entries! "
                        f"Subtitles will not appear. File content preview: {content[:500]}"
                    )
        except Exception as e:
            logger.error(f"Failed to read ASS file: {e}", exc_info=True)
    else:
        video_filter = base_filter
        logger.debug(f"Processing without subtitles | srt_path={srt_path_str or 'None'}")
    
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
    
    # Log the full command for debugging subtitle issues
    if use_subtitles:
        full_cmd_str = ' '.join(cmd)
        logger.info(
            f"FFmpeg command with subtitles | "
            f"subtitle_file={abs_path} | "
            f"filter={video_filter[:200]}... | "
            f"full_cmd_preview={full_cmd_str[:300]}..."
        )
    
    _run_ffmpeg(
        cmd=cmd,
        operation=f"cut, crop and burn (codec={video_codec}, start={start_time}s, end={end_time}s, subtitles={'yes' if use_subtitles else 'no'})",
    )

