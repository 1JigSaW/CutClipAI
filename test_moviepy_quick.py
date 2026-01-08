#!/usr/bin/env python3
"""
Quick test script for MoviePy subtitle and crop functionality.
Usage: python3 test_moviepy_quick.py <video_path> [start_sec] [end_sec]
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.video.moviepy_subtitles import create_optimized_clip
from app.core.logger import get_logger

logger = get_logger(__name__)


def test_moviepy_processing(
    video_path: str,
    start_time: float = 0.0,
    end_time: float = 10.0
):
    """
    Quick test of MoviePy subtitle and crop functionality.
    """
    print(f"🚀 Testing MoviePy processing")
    print(f"📹 Video: {video_path}")
    print(f"⏰ Time range: {start_time:.1f}s - {end_time:.1f}s")
    print()
    
    # Check if video exists
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        return False
    
    # Create output directory
    output_dir = Path("data/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Output file
    output_path = output_dir / f"test_moviepy_{start_time:.0f}_{end_time:.0f}.mp4"
    
    print(f"📝 Processing video with MoviePy...")
    print(f"   - Cropping to 9:16 aspect ratio")
    print(f"   - Adding subtitles from AssemblyAI cache")
    print(f"   - Output: {output_path}")
    print()
    
    try:
        success = create_optimized_clip(
            video_path=video_path_obj,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            add_subtitles=True,
            font_family="Arial",
            font_size=50,
            font_color="#FFFF00"
        )
        
        if success and output_path.exists():
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ SUCCESS!")
            print(f"   Output file: {output_path}")
            print(f"   File size: {file_size_mb:.2f} MB")
            print()
            print(f"🎬 Open the video to check:")
            print(f"   - Video is cropped to 9:16 (vertical)")
            print(f"   - Subtitles appear at 75% height")
            print(f"   - Face-centered crop (if faces detected)")
            return True
        else:
            print(f"❌ FAILED: Output file not created")
            print(f"   success={success}, exists={output_path.exists()}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR during processing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_moviepy_quick.py <video_path> [start_sec] [end_sec]")
        print()
        print("Example:")
        print("  python3 test_moviepy_quick.py data/test_output/test_vertical.mp4 0 10")
        sys.exit(1)
    
    video_path = sys.argv[1]
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    end = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    
    success = test_moviepy_processing(video_path, start, end)
    sys.exit(0 if success else 1)

