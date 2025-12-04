import sys
from pathlib import Path

from app.core.config import settings
from app.services.video.subtitles import SubtitlesService
from app.utils.video.ffmpeg import burn_subtitles

def test_subtitles():
    """
    Test subtitle generation and burning on a video file.
    """
    if len(sys.argv) < 2:
        print("Usage: python test_subtitles.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Testing subtitles on: {video_path}")

    subtitles_service = SubtitlesService()

    print("Generating ASS subtitle file...")
    ass_path = subtitles_service.generate_srt(
        video_path=video_path,
    )

    print(f"ASS file generated: {ass_path}")

    print("Burning subtitles into video...")
    output_path = subtitles_service.burn_subtitles(
        video_path=video_path,
        srt_path=ass_path,
    )

    print(f"Output video with subtitles: {output_path}")
    print("Test completed!")

if __name__ == "__main__":
    test_subtitles()

