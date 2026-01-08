import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from app.services.video.pipeline import VideoPipeline
from app.core.config import settings
from app.utils.video.files import create_temp_dir

async def test_single_clip(video_path: str, start: float, end: float):
    """
    Test the EXACT processing logic used in the app.
    """
    print(f"🚀 Testing processing for: {video_path}")
    print(f"⏰ Range: {start}s - {end}s")
    
    pipeline = VideoPipeline()
    output_dir = Path("data/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock transcript data if cache doesn't exist
    cache_path = Path(video_path).with_suffix('.assemblyai_cache.json')
    if not cache_path.exists():
        print("📝 Generating dummy transcription for testing (MS format)...")
        # REAL AssemblyAI uses MILLISECONDS
        dummy_data = {
            "words": [
                {"text": "test", "start": int(start * 1000), "end": int((start + 1) * 1000)},
                {"text": "subtitles", "start": int((start + 1) * 1000), "end": int((start + 2) * 1000)},
                {"text": "working", "start": int((start + 2) * 1000), "end": int((start + 3) * 1000)}
            ]
        }
        with open(cache_path, 'w') as f:
            json.dump(dummy_data, f)

    moment = {
        "start": start,
        "end": end
    }
    
    # Run the internal process_single_clip logic
    # We copy the logic here to verify it
    try:
        from app.services.video.assemblyai_subtitles import AssemblyAISubtitlesService
        from app.utils.video.ffmpeg import cut_crop_and_burn_optimized
        
        final_path = output_dir / "test_final_with_subs.mp4"
        
        print("1. Generating ASS subtitles from AssemblyAI cache...")
        subtitle_service = AssemblyAISubtitlesService()
        ass_subtitle_path = subtitle_service.generate_srt(
            video_path=video_path,
            clip_start_time=start,
            clip_end_time=end,
        )
        
        if ass_subtitle_path:
            print(f"   ✅ Subtitles generated: {ass_subtitle_path}")
        else:
            print("   ⚠️ No subtitles generated (will process without)")
        
        print("2. Processing video with FFmpeg (cut + crop + burn subtitles in one pass)...")
        cut_crop_and_burn_optimized(
            input_path=video_path,
            output_path=str(final_path),
            start_time=start,
            end_time=end,
            srt_path=ass_subtitle_path,
        )
        
        if final_path.exists():
            print(f"✅ SUCCESS! Check output at: {final_path}")
        else:
            print("❌ Failed to create output video.")
            
    except Exception as e:
        print(f"💥 ERROR during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_processing.py <path_to_video> [start_sec] [end_sec]")
        sys.exit(1)
        
    v_path = sys.argv[1]
    s = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    e = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    
    asyncio.run(test_single_clip(v_path, s, e))

