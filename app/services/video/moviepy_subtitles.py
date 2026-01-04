"""
MoviePy-based subtitle generation service.
Uses the same approach as SupoClip - creates TextClip objects and composites them.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

try:
    from moviepy import VideoFileClip, CompositeVideoClip, TextClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False
        VideoFileClip = None
        CompositeVideoClip = None
        TextClip = None

from app.core.logger import get_logger

logger = get_logger(__name__)


class VideoProcessor:
    """Handles video processing operations with optimized settings."""

    def __init__(
        self,
        font_family: str = "Arial",
        font_size: int = 36,
        font_color: str = "#FFFFFF",
    ):
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = font_color
        
        # Search for a valid font on macOS
        macos_fonts = [
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "Arial",
            "Helvetica"
        ]
        
        self.font_path = "Arial" # Default
        for font in macos_fonts:
            if font.startswith("/") and Path(font).exists():
                self.font_path = font
                break
        
        logger.info(f"VideoProcessor initialized | font={self.font_path} | font_size={self.font_size}")


def load_cached_transcript_data(video_path: Path) -> Optional[dict]:
    """Load cached AssemblyAI transcript data."""
    if isinstance(video_path, str):
        video_path = Path(video_path)
    
    # Try multiple cache path strategies
    cache_paths = [
        video_path.with_suffix('.assemblyai_cache.json'),
        video_path.parent / f"{video_path.stem}.assemblyai_cache.json",
    ]
    
    # Also try to find cache in parent directory (for trimmed videos)
    if 'trimmed' in str(video_path):
        original_name = str(video_path).replace('trimmed_', '')
        cache_paths.append(Path(original_name).with_suffix('.assemblyai_cache.json'))
        cache_paths.append(video_path.parent.parent / Path(original_name).with_suffix('.assemblyai_cache.json').name)
    
    cache_path = None
    for cp in cache_paths:
        if cp.exists():
            cache_path = cp
            break
    
    if not cache_path:
        logger.warning(f"AssemblyAI cache not found | tried_paths={[str(p) for p in cache_paths]} | video_path={video_path}")
        return None

    try:
        with open(cache_path, 'r') as f:
            data = json.load(f)
            words_count = len(data.get('words', []))
            logger.info(f"Loaded transcript cache | path={cache_path} | words={words_count}")
            if words_count > 0:
                first_word = data['words'][0]
                last_word = data['words'][-1]
            first_word_start_sec = first_word.get('start', 0)
            last_word_end_sec = last_word.get('end', 0)
            logger.info(
                f"Transcript range | first_word_start={first_word_start_sec:.2f}s ({int(first_word_start_sec * 1000)}ms) | "
                f"last_word_end={last_word_end_sec:.2f}s ({int(last_word_end_sec * 1000)}ms)"
            )
            return data
    except Exception as e:
        logger.warning(f"Failed to load transcript cache: {e}")
        return None


def create_assemblyai_subtitles_moviepy(
    video_path: Path,
    clip_start: float,
    clip_end: float,
    video_width: int,
    video_height: int,
    font_family: str = "Arial",
    font_size: int = 36,
    font_color: str = "#FFFFFF",
) -> List[TextClip]:
    """
    Create subtitles using AssemblyAI's precise word timing with MoviePy.
    Exactly like SupoClip implementation.
    """
    if not MOVIEPY_AVAILABLE or TextClip is None:
        logger.error("MoviePy TextClip not available!")
        return []
    
    if isinstance(video_path, str):
        video_path = Path(video_path)
    transcript_data = load_cached_transcript_data(video_path)

    if not transcript_data or not transcript_data.get('words'):
        logger.warning(f"No cached transcript data available for subtitles | video_path={video_path}")
        return []

    total_words = len(transcript_data['words'])
    clip_start_ms = int(clip_start * 1000)
    clip_end_ms = int(clip_end * 1000)
    
    logger.info(
        f"Creating subtitles | clip_start={clip_start:.2f}s ({clip_start_ms}ms) | "
        f"clip_end={clip_end:.2f}s ({clip_end_ms}ms) | total_words={total_words}"
    )

    relevant_words = []
    for word_data in transcript_data['words']:
        # Time in cache is stored in SECONDS, not milliseconds!
        word_start_sec = word_data['start']
        word_end_sec = word_data['end']
        
        # Convert to milliseconds for comparison
        word_start_ms = int(word_start_sec * 1000)
        word_end_ms = int(word_end_sec * 1000)

        if word_start_ms < clip_end_ms and word_end_ms > clip_start_ms:
            # Convert to relative time in seconds for MoviePy
            relative_start = max(0, (word_start_ms - clip_start_ms) / 1000.0)
            relative_end = min(
                (clip_end_ms - clip_start_ms) / 1000.0,
                (word_end_ms - clip_start_ms) / 1000.0
            )

            if relative_end > relative_start:
                word_info = {
                    'text': word_data['text'],
                    'start': relative_start,
                    'end': relative_end,
                    'confidence': word_data.get('confidence', 1.0)
                }
                relevant_words.append(word_info)
                logger.debug(
                    f"Word found in clip | text='{word_data['text']}' | "
                    f"absolute_time={word_start_sec:.2f}s-{word_end_sec:.2f}s | "
                    f"relative_time={relative_start:.2f}s-{relative_end:.2f}s"
                )

    if not relevant_words:
        first_word = transcript_data['words'][0] if transcript_data['words'] else None
        last_word = transcript_data['words'][-1] if transcript_data['words'] else None
        first_word_start_sec = first_word['start'] if first_word else 0
        last_word_end_sec = last_word['end'] if last_word else 0
        
        # Log nearby words for debugging
        nearby_words = []
        for word_data in transcript_data['words'][:10]:  # Check first 10 words
            word_start_sec = word_data['start']
            word_end_sec = word_data['end']
            if abs(word_start_sec - clip_start) < 5.0:  # Within 5 seconds
                nearby_words.append(f"'{word_data['text']}' at {word_start_sec:.2f}s")
        
        logger.warning(
            f"No words found in clip timerange | "
            f"clip_start={clip_start:.2f}s ({clip_start_ms}ms) | "
            f"clip_end={clip_end:.2f}s ({clip_end_ms}ms) | "
            f"total_words={total_words} | "
            f"first_word_start={first_word_start_sec:.2f}s ({int(first_word_start_sec * 1000)}ms) | "
            f"last_word_end={last_word_end_sec:.2f}s ({int(last_word_end_sec * 1000)}ms) | "
            f"nearby_words={nearby_words[:3] if nearby_words else 'none'}"
        )
        return []
    
    logger.info(f"Found {len(relevant_words)} relevant words for subtitles")

    subtitle_clips = []
    processor = VideoProcessor(font_family, font_size, font_color)

    # Calculate font size - increased max limit for better visibility
    # For 1080px width: font_size * (1080/720) = font_size * 1.5
    calculated_font_size = max(24, min(70, int(font_size * (video_width / 720))))
    final_font_size = calculated_font_size

    words_per_subtitle = 3
    previous_end = 0  # Track end time of previous subtitle to prevent overlap
    min_gap_between_subtitles = 0.3  # Minimum gap in seconds between subtitles (old must disappear before new appears)
    
    for i in range(0, len(relevant_words), words_per_subtitle):
        word_group = relevant_words[i:i + words_per_subtitle]

        if not word_group:
            continue

        # Calculate timing based on words, but ensure no overlap with previous subtitle
        clip_duration = clip_end - clip_start
        
        # Start slightly earlier (0.1s) for better sync, but ensure gap after previous subtitle
        word_start_time = word_group[0]['start']
        word_end_time = word_group[-1]['end']
        
        # Calculate desired start time (slightly before word starts)
        desired_start = max(0, word_start_time - 0.1)
        
        # Ensure minimum gap after previous subtitle ends
        # Next subtitle can only start after previous_end + min_gap
        segment_start = max(desired_start, previous_end + min_gap_between_subtitles)
        
        # End exactly when word ends (no delay to prevent overlap)
        segment_end = min(clip_duration, word_end_time)
        
        # If start time is pushed too far, adjust end time to maintain minimum duration
        if segment_start >= segment_end:
            segment_end = segment_start + 0.2  # Minimum duration
        
        segment_duration = segment_end - segment_start

        if segment_duration < 0.1:
            continue
        
        # Update previous_end for next iteration (this is when subtitle fully disappears)
        previous_end = segment_end

        text = ' '.join(word['text'] for word in word_group)

        try:
            logger.info(
                f"Creating subtitle TextClip | text='{text[:50]}...' | "
                f"start={segment_start:.2f}s | end={segment_end:.2f}s | "
                f"duration={segment_duration:.2f}s | font={processor.font_path} | "
                f"font_size={final_font_size}"
            )
            
            # Create text clip with robust parameters
            # Add newlines to the text to prevent clipping by ImageMagick
            # We add an extra newline and a space at the bottom to give even more "air" for descenders
            display_text = f"\n{text}\n \n"
            
            try:
                # Primary attempt: MoviePy 2.x style
                text_clip = TextClip(
                    text=display_text,
                    font=processor.font_path,
                    font_size=final_font_size,
                    color=font_color,
                    stroke_color='black',
                    stroke_width=2,
                    method='label',
                    text_align='center'
                )
            except Exception as e:
                logger.warning(f"Failed to create TextClip with 'text' (MoviePy 2.x style): {e}")
                try:
                    # Fallback: MoviePy 1.x style
                    from moviepy.video.VideoClip import TextClip as TC
                    text_clip = TC(
                        txt=display_text,
                        font=processor.font_path,
                        fontsize=final_font_size,
                        color=font_color,
                        stroke_color='black',
                        stroke_width=2,
                        method='label'
                    )
                except Exception as e2:
                    logger.error(f"Failed to create TextClip with fallback: {e2}")
                    continue

            # Set duration and start time
            text_clip = text_clip.with_duration(segment_duration).with_start(segment_start)

            # Get actual rendered size
            text_width, text_height = (0, 0)
            if hasattr(text_clip, 'size') and text_clip.size:
                text_width, text_height = text_clip.size
            
            # Position the CENTER of the text at 75% height
            # Since we added extra newlines, we need to be careful with centering.
            # We'll shift it up by a few extra pixels just to be 100% safe from the bottom.
            desired_center_y = int(video_height * 0.75) - 5
            
            if text_height > 0:
                vertical_position = desired_center_y - (text_height // 2)
            else:
                # Fallback if size is unknown
                vertical_position = desired_center_y - (final_font_size // 2) - 60
            
            # Final boundary check: don't let it go too low
            max_allowed_y = video_height - (text_height if text_height > 0 else 150) - 20
            if vertical_position > max_allowed_y:
                vertical_position = max_allowed_y
            
            # Set position
            text_clip = text_clip.with_position(('center', vertical_position))
            
            logger.info(
                f"Subtitle created | text='{text}' | "
                f"start={segment_start:.2f}s | duration={segment_duration:.2f}s | "
                f"v_pos={vertical_position} | size={text_width}x{text_height}"
            )

            subtitle_clips.append(text_clip)

        except Exception as e:
            logger.error(f"Failed to create subtitle for '{text}': {e}", exc_info=True)
            continue

    logger.info(
        f"Created {len(subtitle_clips)} subtitle elements from AssemblyAI data | "
        f"total_relevant_words={len(relevant_words)} | "
        f"words_per_subtitle={words_per_subtitle}"
    )
    
    if subtitle_clips:
        logger.info("Subtitle details:")
        for idx, sub_clip in enumerate(subtitle_clips):
            logger.info(
                f"  Subtitle {idx+1}: start={sub_clip.start:.2f}s | "
                f"duration={sub_clip.duration:.2f}s | "
                f"position={sub_clip.pos if hasattr(sub_clip, 'pos') else 'N/A'}"
            )
    
    return subtitle_clips


def create_clip_with_moviepy_subtitles(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    add_subtitles: bool = True,
    font_family: str = "Arial",
    font_size: int = 36,
    font_color: str = "#FFFFFF",
) -> bool:
    """
    Create optimized 9:16 clip with AssemblyAI subtitles using MoviePy.
    Exactly like SupoClip implementation.
    """
    if not MOVIEPY_AVAILABLE:
        logger.error("MoviePy is not available! Cannot create clips with subtitles.")
        return False
    
    try:
        video_path_obj = Path(video_path)
        output_path_obj = Path(output_path)
        
        duration = end_time - start_time
        if duration <= 0:
            logger.error(f"Invalid clip duration: {duration:.1f}s")
            return False

        logger.info(f"Creating clip with MoviePy: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")

        video = VideoFileClip(str(video_path))

        # Check if clip is within video bounds
        if start_time >= video.duration:
            logger.warning(
                f"Start time {start_time:.1f}s exceeds video duration {video.duration:.1f}s. "
                f"Skipping this clip."
            )
            video.close()
            return False

        # Adjust end_time if it exceeds video duration
        if end_time > video.duration:
            logger.warning(
                f"End time {end_time:.1f}s exceeds video duration {video.duration:.1f}s. "
                f"Adjusting to {video.duration:.1f}s"
            )
            end_time = video.duration
        
        # Check if we have valid duration after adjustment
        if end_time <= start_time:
            logger.warning(
                f"Invalid clip duration after adjustment: start={start_time:.1f}s, end={end_time:.1f}s. "
                f"Skipping this clip."
            )
            video.close()
            return False
        # MoviePy 2.x uses subclipped, 1.x uses subclip
        try:
            clip = video.subclipped(start_time, end_time)
        except AttributeError:
            clip = video.subclip(start_time, end_time)

        # Robust 9:16 transformation without stretching
        # Step 1: Resize height to 1920, keeping aspect ratio
        target_height = 1920
        target_width = 1080
        
        try:
            # Try MoviePy 2.x
            rescaled_clip = clip.resized(height=target_height)
        except AttributeError:
            # Fallback for MoviePy 1.x
            rescaled_clip = clip.resize(height=target_height)
            
        # Step 2: Crop the width to exactly 1080 from the center
        current_w, current_h = rescaled_clip.size
        x1 = max(0, int((current_w - target_width) / 2))
        y1 = 0
        x2 = min(current_w, x1 + target_width)
        y2 = target_height
        
        try:
            # Try universal crop method
            cropped_clip = rescaled_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
        except AttributeError:
            # Fallback for some versions
            try:
                cropped_clip = rescaled_clip.with_crop(x1=x1, y1=y1, x2=x2, y2=y2)
            except AttributeError:
                cropped_clip = rescaled_clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)

        # Final safety check: if we somehow don't have exactly 1080x1920, force it
        if cropped_clip.size != (target_width, target_height):
            try:
                cropped_clip = cropped_clip.resized((target_width, target_height))
            except AttributeError:
                cropped_clip = cropped_clip.resize(new_size=(target_width, target_height))

        final_clips = [cropped_clip]

        if add_subtitles:
            logger.info(f"Adding subtitles to clip | start_time={start_time:.2f} | end_time={end_time:.2f}")
            subtitle_clips = create_assemblyai_subtitles_moviepy(
                video_path_obj,
                start_time,
                end_time,
                target_width,
                target_height,
                font_family,
                font_size,
                font_color
            )
            
            if subtitle_clips:
                logger.info(f"Successfully created {len(subtitle_clips)} subtitle clips")
                final_clips.extend(subtitle_clips)
            else:
                logger.warning("No subtitle clips were generated for this segment")

        if len(final_clips) > 1:
            logger.info(f"Compositing {len(final_clips)} elements (1 video + {len(final_clips)-1} subtitles)")
            # In MoviePy 2.x, it's safer to provide the size of the background video
            final_clip = CompositeVideoClip(final_clips, size=cropped_clip.size)
            # Ensure the duration is set to match the video clip
            final_clip = final_clip.with_duration(cropped_clip.duration)
        else:
            logger.info("No subtitles to add, using video clip only")
            final_clip = cropped_clip

        processor = VideoProcessor(font_family, font_size, font_color)
        encoding_settings = {
            "codec": "libx264",
            "audio_codec": "aac",
            "bitrate": "8000k",
            "audio_bitrate": "256k",
            "preset": "medium",
            "ffmpeg_params": ["-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.1"]
        }

        import tempfile
        import uuid
        temp_audio_path = str(Path(output_path_obj).parent / f'temp-audio-{uuid.uuid4().hex[:8]}.m4a')
        
        logger.info(
            f"Writing video file | output_path={output_path_obj} | "
            f"duration={final_clip.duration:.2f}s | has_subtitles={len(final_clips) > 1} | "
            f"total_clips_in_composition={len(final_clips)}"
        )
        
        # Final verification before writing
        if len(final_clips) > 1:
            logger.info("FINAL VERIFICATION - Subtitles before write:")
            for idx, clip_item in enumerate(final_clips):
                if idx == 0:
                    logger.info(f"  [VIDEO] Clip {idx}: duration={clip_item.duration:.2f}s")
                else:
                    subtitle_clip = clip_item
                    clip_text = 'N/A'
                    if hasattr(subtitle_clip, 'txt'):
                        clip_text = str(subtitle_clip.txt)[:50]
                    elif hasattr(subtitle_clip, 'text'):
                        clip_text = str(subtitle_clip.text)[:50]
                    
                    logger.info(
                        f"  [SUBTITLE] Clip {idx}: text='{clip_text}' | "
                        f"start={subtitle_clip.start:.2f}s | duration={subtitle_clip.duration:.2f}s | "
                        f"size={subtitle_clip.size if hasattr(subtitle_clip, 'size') else 'N/A'}"
                    )
        
        if final_clip.duration is None or final_clip.duration < 0.5:
            logger.error(f"Final clip duration is too short or invalid: {final_clip.duration}")
            return False

        try:
            final_clip.write_videofile(
                str(output_path_obj),
                temp_audiofile=temp_audio_path,
                remove_temp=True,
                logger=None,
                **encoding_settings
            )
            
            output_size = Path(output_path_obj).stat().st_size if Path(output_path_obj).exists() else 0
            logger.info(
                f"Video file written successfully | path={output_path_obj} | "
                f"size={output_size} bytes ({output_size / 1024 / 1024:.2f} MB) | "
                f"has_subtitles={len(final_clips) > 1} | subtitles_count={len(final_clips) - 1}"
            )
        except Exception as e:
            logger.error(f"Failed to write video file: {e}", exc_info=True)
            raise
        finally:
            if Path(temp_audio_path).exists():
                try:
                    Path(temp_audio_path).unlink()
                except:
                    pass

        final_clip.close()
        clip.close()
        video.close()

        logger.info(f"Successfully created clip with MoviePy: {output_path_obj}")
        return True

    except Exception as e:
        logger.error(f"Failed to create clip with MoviePy: {e}", exc_info=True)
        return False

