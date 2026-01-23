"""
MoviePy-based subtitle generation service.
Exact implementation from SupoClip for consistency.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

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

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

from app.core.logger import get_logger

logger = get_logger(__name__)


class VideoProcessor:
    """Handles video processing operations with optimized settings."""

    def __init__(
        self,
        font_family: str = "Arial",
        font_size: int = 24,
        font_color: str = "#FFFFFF"
    ):
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = font_color
        
        # Try to find font in CutClipAI fonts directory
        fonts_dir = Path(__file__).parent.parent.parent.parent / "fonts"
        if fonts_dir.exists():
            font_path = fonts_dir / f"{font_family}.ttf"
            if font_path.exists():
                self.font_path = str(font_path)
                logger.info(f"✅ Using custom font from fonts directory: {self.font_path}")
            else:
                logger.info(f"Custom font not found, searching for system font...")
                self.font_path = self._find_system_font()
        else:
            logger.info(f"Fonts directory not found, searching for system font...")
            self.font_path = self._find_system_font()
        
        logger.info(f"📝 Final font path: {self.font_path}")
    
    def _find_system_font(self) -> str:
        """Find available system font for subtitles."""
        logger.info("🔍 Searching for system fonts...")
        
        # Try common system fonts that are usually available in Linux
        # Liberation is installed in Dockerfile, so check it first
        system_fonts = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf",
        ]
        
        for font_path in system_fonts:
            font_path_obj = Path(font_path)
            if font_path_obj.exists():
                font_size = font_path_obj.stat().st_size
                logger.info(
                    f"✅ Found system font: {font_path} | "
                    f"exists=True | size={font_size} bytes"
                )
                return font_path
            else:
                logger.debug(f"❌ Font not found: {font_path}")
        
        # If no system font found, try to use PIL's default font
        logger.warning("No system fonts found at expected paths, trying PIL default font...")
        try:
            from PIL import ImageFont
            try:
                default_font = ImageFont.load_default()
                logger.info("✅ Using PIL default font (None)")
                return None  # None means use PIL default
            except Exception as e:
                logger.error(f"❌ PIL default font failed: {e}")
        except ImportError:
            logger.error("❌ PIL ImageFont not available")
        
        # Last resort: try Liberation Sans by name (fontconfig might find it)
        logger.warning(
            f"⚠️ No system fonts found, trying 'Liberation Sans' by name as last resort. "
            f"This may fail if fontconfig is not configured."
        )
        return "Liberation Sans"

    def get_optimal_encoding_settings(
        self,
        target_quality: str = "high"
    ) -> Dict[str, Any]:
        """Get optimal encoding settings for different quality levels."""
        settings = {
            "high": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "8000k",
                "audio_bitrate": "256k",
                "preset": "medium",
                "ffmpeg_params": [
                    "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    "-profile:v", "main",
                    "-level", "4.1"
                ]
            },
            "medium": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "4000k",
                "audio_bitrate": "192k",
                "preset": "fast",
                "ffmpeg_params": ["-crf", "23", "-pix_fmt", "yuv420p"]
            }
        }
        return settings.get(target_quality, settings["high"])


def round_to_even(value: int) -> int:
    """Round integer to nearest even number for H.264 compatibility."""
    return value - (value % 2)


def filter_face_outliers(
    face_centers: List[Tuple[int, int, int, float]]
) -> List[Tuple[int, int, int, float]]:
    """Remove face detections that are outliers (likely false positives)."""
    if len(face_centers) < 3:
        return face_centers

    try:
        if not CV2_AVAILABLE or np is None:
            return face_centers

        # Calculate median position
        x_positions = [x for x, y, area, conf in face_centers]
        y_positions = [y for x, y, area, conf in face_centers]

        median_x = np.median(x_positions)
        median_y = np.median(y_positions)

        # Calculate standard deviation
        std_x = np.std(x_positions)
        std_y = np.std(y_positions)

        # Filter out faces that are more than 2 standard deviations away
        filtered_faces = []
        for face in face_centers:
            x, y, area, conf = face
            if (abs(x - median_x) <= 2 * std_x and abs(y - median_y) <= 2 * std_y):
                filtered_faces.append(face)

        logger.info(
            f"Filtered {len(face_centers)} -> {len(filtered_faces)} faces (removed outliers)"
        )
        return filtered_faces if filtered_faces else face_centers

    except Exception as e:
        logger.warning(f"Error filtering face outliers: {e}")
        return face_centers


def detect_faces_in_clip(
    video_clip: VideoFileClip,
    start_time: float,
    end_time: float
) -> List[Tuple[int, int, int, float]]:
    """
    Improved face detection using multiple methods and temporal consistency.
    Returns list of (x, y, area, confidence) tuples.
    """
    if not CV2_AVAILABLE:
        logger.warning("OpenCV not available, face detection disabled")
        return []

    face_centers = []

    try:
        # Try to use MediaPipe (most accurate)
        mp_face_detection = None
        try:
            import mediapipe as mp
            mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5
            )
            logger.info("Using MediaPipe face detector")
        except ImportError:
            logger.info("MediaPipe not available, falling back to OpenCV")
        except Exception as e:
            logger.warning(f"MediaPipe face detector failed to initialize: {e}")

        # Initialize OpenCV face detectors as fallback
        haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # Try to load DNN face detector (more accurate than Haar)
        dnn_net = None
        try:
            prototxt_path = cv2.data.haarcascades.replace(
                'haarcascades',
                'opencv_face_detector.pbtxt'
            )
            model_path = cv2.data.haarcascades.replace(
                'haarcascades',
                'opencv_face_detector_uint8.pb'
            )

            if os.path.exists(prototxt_path) and os.path.exists(model_path):
                dnn_net = cv2.dnn.readNetFromTensorflow(model_path, prototxt_path)
                logger.info("OpenCV DNN face detector loaded as backup")
            else:
                logger.info("OpenCV DNN face detector not available")
        except Exception:
            logger.info("OpenCV DNN face detector failed to load")

        # Sample more frames for better face detection (every 0.5 seconds)
        duration = end_time - start_time
        sample_interval = min(0.5, duration / 10)
        sample_times = []

        current_time = start_time
        while current_time < end_time:
            sample_times.append(current_time)
            current_time += sample_interval

        # Ensure we always sample the middle and end
        if duration > 1.0:
            middle_time = start_time + duration / 2
            if middle_time not in sample_times:
                sample_times.append(middle_time)

        sample_times = [t for t in sample_times if t < end_time]
        logger.info(f"Sampling {len(sample_times)} frames for face detection")

        for sample_time in sample_times:
            try:
                frame = video_clip.get_frame(sample_time)
                height, width = frame.shape[:2]
                detected_faces = []

                # Try MediaPipe first (most accurate)
                if mp_face_detection is not None:
                    try:
                        results = mp_face_detection.process(frame)

                        if results.detections:
                            for detection in results.detections:
                                bbox = detection.location_data.relative_bounding_box
                                confidence = detection.score[0]

                                x = int(bbox.xmin * width)
                                y = int(bbox.ymin * height)
                                w = int(bbox.width * width)
                                h = int(bbox.height * height)

                                if w > 30 and h > 30:
                                    detected_faces.append((x, y, w, h, confidence))
                    except Exception as e:
                        logger.warning(
                            f"MediaPipe detection failed for frame at {sample_time}s: {e}"
                        )

                # If MediaPipe didn't find faces, try DNN detector
                if not detected_faces and dnn_net is not None:
                    try:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        blob = cv2.dnn.blobFromImage(
                            frame_bgr,
                            1.0,
                            (300, 300),
                            [104, 117, 123]
                        )
                        dnn_net.setInput(blob)
                        detections = dnn_net.forward()

                        for i in range(detections.shape[2]):
                            confidence = detections[0, 0, i, 2]
                            if confidence > 0.5:
                                x1 = int(detections[0, 0, i, 3] * width)
                                y1 = int(detections[0, 0, i, 4] * height)
                                x2 = int(detections[0, 0, i, 5] * width)
                                y2 = int(detections[0, 0, i, 6] * height)

                                w = x2 - x1
                                h = y2 - y1

                                if w > 30 and h > 30:
                                    detected_faces.append((x1, y1, w, h, confidence))
                    except Exception as e:
                        logger.warning(
                            f"DNN detection failed for frame at {sample_time}s: {e}"
                        )

                # If still no faces found, use Haar cascade
                if not detected_faces:
                    try:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

                        faces = haar_cascade.detectMultiScale(
                            gray,
                            scaleFactor=1.05,
                            minNeighbors=3,
                            minSize=(40, 40),
                            maxSize=(int(width*0.7), int(height*0.7))
                        )

                        for (x, y, w, h) in faces:
                            face_area = w * h
                            relative_size = face_area / (width * height)
                            confidence = min(0.9, 0.3 + relative_size * 2)
                            detected_faces.append((x, y, w, h, confidence))
                    except Exception as e:
                        logger.warning(
                            f"Haar cascade detection failed for frame at {sample_time}s: {e}"
                        )

                # Process detected faces
                for (x, y, w, h, confidence) in detected_faces:
                    face_center_x = x + w // 2
                    face_center_y = y + h // 2
                    face_area = w * h

                    # Filter out very small or very large faces
                    frame_area = width * height
                    relative_area = face_area / frame_area

                    if 0.005 < relative_area < 0.3:
                        face_centers.append(
                            (face_center_x, face_center_y, face_area, confidence)
                        )

            except Exception as e:
                logger.warning(
                    f"Error detecting faces in frame at {sample_time}s: {e}"
                )
                continue

        # Close MediaPipe detector
        if mp_face_detection is not None:
            mp_face_detection.close()

        # Remove outliers (faces that are very far from the median position)
        if len(face_centers) > 2:
            face_centers = filter_face_outliers(face_centers)

        logger.info(f"Detected {len(face_centers)} reliable face centers")
        return face_centers

    except Exception as e:
        logger.error(f"Error in face detection: {e}")
        return []


def detect_optimal_crop_region(
    video_clip: VideoFileClip,
    start_time: float,
    end_time: float,
    target_ratio: float = 9/16
) -> Tuple[int, int, int, int]:
    """Detect optimal crop region using improved face detection."""
    try:
        original_width, original_height = video_clip.size

        # Calculate target dimensions and ensure they're even
        if original_width / original_height > target_ratio:
            new_width = round_to_even(int(original_height * target_ratio))
            new_height = round_to_even(original_height)
        else:
            new_width = round_to_even(original_width)
            new_height = round_to_even(int(original_width / target_ratio))

        # Try improved face detection
        face_centers = detect_faces_in_clip(video_clip, start_time, end_time)

        # Calculate crop position
        if face_centers:
            # Use weighted average of face centers with temporal consistency
            total_weight = sum(
                area * confidence for _, _, area, confidence in face_centers
            )
            if total_weight > 0:
                weighted_x = sum(
                    x * area * confidence
                    for x, y, area, confidence in face_centers
                ) / total_weight
                weighted_y = sum(
                    y * area * confidence
                    for x, y, area, confidence in face_centers
                ) / total_weight

                # Add slight bias towards upper portion for better face framing
                weighted_y = max(0, weighted_y - new_height * 0.1)

                x_offset = max(
                    0,
                    min(int(weighted_x - new_width // 2), original_width - new_width)
                )
                y_offset = max(
                    0,
                    min(int(weighted_y - new_height // 2), original_height - new_height)
                )

                logger.info(
                    f"Face-centered crop: {len(face_centers)} faces detected with improved algorithm"
                )
            else:
                # Center crop
                x_offset = (
                    (original_width - new_width) // 2
                    if original_width > new_width
                    else 0
                )
                y_offset = (
                    (original_height - new_height) // 2
                    if original_height > new_height
                    else 0
                )
        else:
            # Center crop
            x_offset = (
                (original_width - new_width) // 2
                if original_width > new_width
                else 0
            )
            y_offset = (
                (original_height - new_height) // 2
                if original_height > new_height
                else 0
            )
            logger.info("Using center crop (no faces detected)")

        # Ensure offsets are even too
        x_offset = round_to_even(x_offset)
        y_offset = round_to_even(y_offset)

        logger.info(
            f"Crop dimensions: {new_width}x{new_height} at offset ({x_offset}, {y_offset})"
        )
        return (x_offset, y_offset, new_width, new_height)

    except Exception as e:
        logger.error(f"Error in crop detection: {e}")
        # Fallback to center crop
        original_width, original_height = video_clip.size
        if original_width / original_height > target_ratio:
            new_width = round_to_even(int(original_height * target_ratio))
            new_height = round_to_even(original_height)
        else:
            new_width = round_to_even(original_width)
            new_height = round_to_even(int(original_width / target_ratio))

        x_offset = (
            round_to_even((original_width - new_width) // 2)
            if original_width > new_width
            else 0
        )
        y_offset = (
            round_to_even((original_height - new_height) // 2)
            if original_height > new_height
            else 0
        )

        return (x_offset, y_offset, new_width, new_height)


def load_cached_transcript_data(
    video_path: Path
) -> Optional[Dict]:
    """Load cached AssemblyAI transcript data."""
    if isinstance(video_path, str):
        video_path = Path(video_path)
    
    # Try both cache formats for compatibility
    cache_paths = [
        video_path.with_suffix('.transcript_cache.json'),
        video_path.with_suffix('.assemblyai_cache.json')
    ]
    
    for cache_path in cache_paths:
        logger.info(
            f"🔍 Checking cache path | path={cache_path} | exists={cache_path.exists()}"
        )
        if cache_path.exists():
            try:
                cache_size = cache_path.stat().st_size
                logger.info(
                    f"✅ Found cache file | path={cache_path} | size={cache_size} bytes"
                )
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                words_count = len(data.get('words', []))
                logger.info(
                    f"✅ Loaded transcript cache | path={cache_path} | "
                    f"words_count={words_count} | cache_size={cache_size} bytes"
                )
                return data
            except Exception as e:
                logger.error(
                    f"❌ Failed to load transcript cache {cache_path} | error={e}",
                    exc_info=True
                )
                continue
    
    logger.error(
        f"❌ No transcript cache found for {video_path} | "
        f"Tried paths: {[str(p) for p in cache_paths]} | "
        f"Video exists: {video_path.exists()} | "
        f"Video path: {video_path.resolve() if video_path.exists() else 'N/A'}"
    )
    return None


def create_assemblyai_subtitles(
    video_path: Path,
    clip_start: float,
    clip_end: float,
    video_width: int,
    video_height: int,
    font_family: str = "Arial",
    font_size: int = 25,
    font_color: str = "#FFFF00"
) -> List[TextClip]:
    """Create subtitles using AssemblyAI's precise word timing."""
    if not MOVIEPY_AVAILABLE:
        logger.error("MoviePy not available")
        return []
    
    if isinstance(video_path, str):
        video_path = Path(video_path)
    
    logger.info(
        f"🎬 Loading transcript cache for subtitles | video_path={video_path} | "
        f"clip_start={clip_start:.2f}s | clip_end={clip_end:.2f}s"
    )
    
    expected_cache_path = video_path.with_suffix('.assemblyai_cache.json')
    logger.info(
        f"🔍 Looking for cache file | expected_path={expected_cache_path} | "
        f"exists={expected_cache_path.exists()}"
    )
    
    transcript_data = load_cached_transcript_data(video_path)

    if not transcript_data:
        logger.error(
            f"No transcript cache found for subtitles | video_path={video_path} | "
            f"Expected cache: {video_path.with_suffix('.assemblyai_cache.json')}"
        )
        return []
    
    if not transcript_data.get('words'):
        logger.error(
            f"Transcript cache exists but has no words | video_path={video_path} | "
            f"Cache keys: {list(transcript_data.keys())}"
        )
        return []
    
    logger.info(
        f"Found transcript data | words_count={len(transcript_data.get('words', []))}"
    )

    # Convert clip timing to milliseconds
    clip_start_ms = int(clip_start * 1000)
    clip_end_ms = int(clip_end * 1000)

    # Find words that fall within our clip timerange
    relevant_words = []
    logger.info(
        f"Searching for words in clip range | "
        f"clip_start={clip_start:.2f}s ({clip_start_ms}ms) | "
        f"clip_end={clip_end:.2f}s ({clip_end_ms}ms) | "
        f"total_words={len(transcript_data['words'])}"
    )
    
    for word_data in transcript_data['words']:
        # Handle both formats: milliseconds (SupoClip) and seconds (CutClipAI)
        word_start = word_data['start']
        word_end = word_data['end']
        
        # If times are in seconds (less than 1000), convert to milliseconds
        if word_start < 1000 and word_end < 1000:
            word_start_ms = int(word_start * 1000)
            word_end_ms = int(word_end * 1000)
        else:
            word_start_ms = int(word_start)
            word_end_ms = int(word_end)

        # Check if word overlaps with clip
        if word_start_ms < clip_end_ms and word_end_ms > clip_start_ms:
            # Adjust timing relative to clip start
            relative_start = max(0, (word_start_ms - clip_start_ms) / 1000.0)
            relative_end = min(
                (clip_end_ms - clip_start_ms) / 1000.0,
                (word_end_ms - clip_start_ms) / 1000.0
            )

            if relative_end > relative_start:
                relevant_words.append({
                    'text': word_data['text'],
                    'start': relative_start,
                    'end': relative_end,
                    'confidence': word_data.get('confidence', 1.0)
                })
    
    logger.info(f"Found {len(relevant_words)} relevant words for subtitles")

    if not relevant_words:
        logger.warning("No words found in clip timerange")
        return []

    # Group words into subtitle segments (3-4 words per subtitle for readability)
    subtitle_clips = []
    processor = VideoProcessor(font_family, font_size, font_color)

    # Calculate font size based on video width
    calculated_font_size = max(18, min(45, int(font_size * (video_width / 720) * 1.0)))
    final_font_size = calculated_font_size

    words_per_subtitle = 3
    for i in range(0, len(relevant_words), words_per_subtitle):
        word_group = relevant_words[i:i + words_per_subtitle]

        if not word_group:
            continue

        # Calculate segment timing
        segment_start = word_group[0]['start']
        segment_end = word_group[-1]['end']
        segment_duration = segment_end - segment_start

        if segment_duration < 0.1:  # Skip very short segments
            continue

        # Create text
        text = ' '.join(word['text'] for word in word_group)

        try:
            # ROBUST APPROACH: Use 'caption' with fixed size to prevent ANY clipping
            # We set a height that is 2.5x the font size to definitely fit descenders (g, y, p)
            caption_width = int(video_width * 0.9)
            caption_height = int(final_font_size * 2.5)
            
            # Prepare font parameter - use None for PIL default or path for custom font
            font_param = processor.font_path
            
            logger.info(
                f"Creating subtitle TextClip | text='{text[:50]}...' | "
                f"font={font_param} | font_size={final_font_size} | "
                f"caption_size={caption_width}x{caption_height}"
            )
            
            # TextClip can handle None font (uses PIL default) or font path
            text_clip_kwargs = {
                'text': text,
                'font_size': final_font_size,
                'color': font_color,
                'stroke_color': 'black',
                'stroke_width': 2,
                'method': 'caption',
                'size': (caption_width, caption_height),
                'text_align': 'center'
            }
            
            # Only add font parameter if it's not None
            if font_param is not None:
                text_clip_kwargs['font'] = font_param
            
            text_clip = TextClip(**text_clip_kwargs).with_duration(segment_duration).with_start(segment_start)
            
            # Position at 80% down (lower part of the screen)
            # Since we have a tall caption box, we position it so the text is where we want it
            vertical_position = int(video_height * 0.80 - caption_height // 2)
            
            # Ensure we don't hit the very bottom
            if vertical_position + caption_height > video_height - 20:
                vertical_position = video_height - caption_height - 20
            
            if vertical_position < 20:
                vertical_position = 20
            
            logger.info(
                f"Subtitle positioned (Caption method) | text='{text}' | "
                f"box_pos={vertical_position} | box_height={caption_height} | "
                f"font_size={final_font_size} | video_h={video_height}"
            )
            
            # Position the entire box
            text_clip = text_clip.with_position(('center', vertical_position))
            
            # Log final position with descender info
            descender_chars = ['g', 'p', 'q', 'y', 'j']
            has_descenders = any(char in text.lower() for char in descender_chars)
            
            if has_descenders:
                logger.info(f"⚠️ Text contains descenders: '{text}' - using Caption box to protect them")

            logger.info(
                f"✅ Created subtitle clip | text='{text}' | "
                f"start={segment_start:.2f}s | end={segment_end:.2f}s | "
                f"duration={segment_duration:.2f}s | "
                f"position=center,{vertical_position} | "
                f"font_size={final_font_size}"
            )

            subtitle_clips.append(text_clip)

        except Exception as e:
            logger.error(
                f"❌ Failed to create subtitle for '{text}' | "
                f"segment_start={segment_start:.2f}s | segment_end={segment_end:.2f}s | "
                f"error={e}",
                exc_info=True
            )
            continue

    logger.info(
        f"✅ Created {len(subtitle_clips)} subtitle elements from AssemblyAI data | "
        f"video_path={video_path} | clip_range={clip_start:.2f}s-{clip_end:.2f}s"
    )
    if len(subtitle_clips) == 0:
        logger.error(
            f"⚠️ WARNING: No subtitle clips created! | "
            f"relevant_words={len(relevant_words)} | "
            f"video_path={video_path}"
        )
    return subtitle_clips


def create_optimized_clip(
    video_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
    add_subtitles: bool = True,
    font_family: str = "Arial",
    font_size: int = 25,
    font_color: str = "#FFFF00"
) -> bool:
    """Create optimized 9:16 clip with AssemblyAI subtitles."""
    if not MOVIEPY_AVAILABLE:
        logger.error("MoviePy is required for video processing with subtitles")
        return False
    
    if isinstance(video_path, str):
        video_path = Path(video_path)
    if isinstance(output_path, str):
        output_path = Path(output_path)
    
    try:
        duration = end_time - start_time
        if duration <= 0:
            logger.error(f"Invalid clip duration: {duration:.1f}s")
            return False

        logger.info(f"Creating clip: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")

        # Load and process video
        video = VideoFileClip(str(video_path))

        if start_time >= video.duration:
            logger.error(
                f"Start time {start_time}s exceeds video duration {video.duration:.1f}s"
            )
            video.close()
            return False

        end_time = min(end_time, video.duration)
        clip = video.subclipped(start_time, end_time)
        
        # Get original video dimensions
        original_width, original_height = video.size
        clip_width, clip_height = clip.size
        
        logger.info(
            f"Video dimensions | original={original_width}x{original_height} | "
            f"clip={clip_width}x{clip_height} | duration={duration:.1f}s"
        )

        # Get optimal crop region using face detection
        # Always crop to 9:16 regardless of clip duration
        try:
            x_offset, y_offset, new_width, new_height = detect_optimal_crop_region(
                video_clip=video,
                start_time=start_time,
                end_time=end_time,
                target_ratio=9/16
            )
            
            logger.info(
                f"Crop region calculated | offset=({x_offset}, {y_offset}) | "
                f"size={new_width}x{new_height} | target_ratio=9:16"
            )
        except Exception as e:
            logger.warning(
                f"Error in detect_optimal_crop_region, using center crop fallback: {e}"
            )
            # Fallback to simple center crop
            if original_width / original_height > 9/16:
                new_width = round_to_even(int(original_height * 9/16))
                new_height = round_to_even(original_height)
            else:
                new_width = round_to_even(original_width)
                new_height = round_to_even(int(original_width / (9/16)))
            x_offset = round_to_even((original_width - new_width) // 2)
            y_offset = round_to_even((original_height - new_height) // 2)
            logger.info(
                f"Fallback center crop | offset=({x_offset}, {y_offset}) | "
                f"size={new_width}x{new_height}"
            )

        # Verify crop dimensions are valid
        if new_width <= 0 or new_height <= 0:
            logger.error(
                f"Invalid crop dimensions: {new_width}x{new_height}. "
                f"Falling back to center crop."
            )
            # Fallback: center crop
            if original_width / original_height > 9/16:
                new_width = round_to_even(int(original_height * 9/16))
                new_height = round_to_even(original_height)
            else:
                new_width = round_to_even(original_width)
                new_height = round_to_even(int(original_width / (9/16)))
            x_offset = round_to_even((original_width - new_width) // 2)
            y_offset = round_to_even((original_height - new_height) // 2)
            logger.info(
                f"Fallback crop | offset=({x_offset}, {y_offset}) | "
                f"size={new_width}x{new_height}"
            )

        # Ensure crop region is within clip bounds
        x_offset = max(0, min(x_offset, clip_width - new_width))
        y_offset = max(0, min(y_offset, clip_height - new_height))
        new_width = min(new_width, clip_width - x_offset)
        new_height = min(new_height, clip_height - y_offset)
        
        # Ensure dimensions are even
        new_width = round_to_even(new_width)
        new_height = round_to_even(new_height)
        
        logger.info(
            f"Final crop parameters | offset=({x_offset}, {y_offset}) | "
            f"size={new_width}x{new_height} | aspect_ratio={new_width/new_height:.3f}"
        )

        # Crop the clip to 9:16 aspect ratio - ALWAYS apply crop
        # This is critical: we MUST crop to 9:16 for all clips regardless of duration
        try:
            cropped_clip = clip.cropped(
                x1=x_offset,
                y1=y_offset,
                x2=x_offset + new_width,
                y2=y_offset + new_height
            )
            
            # Verify cropped clip dimensions
            cropped_width, cropped_height = cropped_clip.size
            actual_ratio = cropped_width / cropped_height
            logger.info(
                f"Cropped clip dimensions | size={cropped_width}x{cropped_height} | "
                f"ratio={actual_ratio:.3f} (target=0.5625 for 9:16)"
            )
            
            if abs(actual_ratio - 9/16) > 0.1:
                logger.error(
                    f"❌ CRITICAL: Cropped clip ratio {actual_ratio:.3f} differs significantly from "
                    f"target 9:16 (0.5625). Video will be wide instead of vertical!"
                )
                logger.error(
                    f"   Original: {original_width}x{original_height} | "
                    f"Crop params: offset=({x_offset}, {y_offset}) size={new_width}x{new_height}"
                )
        except Exception as e:
            logger.error(
                f"❌ CRITICAL: Failed to crop clip to 9:16: {e}",
                exc_info=True
            )
            # If crop fails, we cannot proceed - this is a critical error
            clip.close()
            video.close()
            raise Exception(
                f"Failed to crop video to 9:16 aspect ratio. "
                f"This is required for all clips. Error: {e}"
            )

        # Add AssemblyAI subtitles
        final_clips = [cropped_clip]

        if add_subtitles:
            logger.info(
                f"Creating subtitles for clip | video_path={video_path} | "
                f"start_time={start_time:.2f}s | end_time={end_time:.2f}s"
            )
            subtitle_clips = create_assemblyai_subtitles(
                video_path=video_path,
                clip_start=start_time,
                clip_end=end_time,
                video_width=new_width,
                video_height=new_height,
                font_family=font_family,
                font_size=font_size,
                font_color=font_color
            )
            logger.info(
                f"Created {len(subtitle_clips)} subtitle clips | "
                f"will_add_to_final={'yes' if subtitle_clips else 'no'}"
            )
            if subtitle_clips:
                final_clips.extend(subtitle_clips)
            else:
                logger.warning(
                    f"No subtitle clips created! Subtitles will not appear in final video."
                )

        # Compose and encode
        final_clip = (
            CompositeVideoClip(final_clips)
            if len(final_clips) > 1
            else cropped_clip
        )

        processor = VideoProcessor(font_family, font_size, font_color)
        encoding_settings = processor.get_optimal_encoding_settings("high")

        # Use unique temp audio file to avoid conflicts in parallel processing
        import uuid
        temp_audiofile = f'temp-audio-{uuid.uuid4().hex[:8]}.m4a'

        final_clip.write_videofile(
            str(output_path),
            temp_audiofile=temp_audiofile,
            remove_temp=True,
            logger=None,
            **encoding_settings
        )

        # Cleanup
        final_clip.close()
        cropped_clip.close()
        clip.close()
        video.close()

        logger.info(f"Successfully created clip: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to create clip: {e}", exc_info=True)
        return False
