import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.utils.video.youtube import download_youtube_video, get_youtube_video_info
from app.core.logger import get_logger

logger = get_logger(__name__)


async def test_age_restricted_video():
    if len(sys.argv) > 1:
        test_url = sys.argv[1].strip()
    else:
        test_url = input("Введите URL age-restricted видео: ").strip()
    
    if not test_url:
        logger.error("URL не введен")
        logger.info("Usage: python test_youtube_age_restricted.py <youtube_url>")
        return
    
    logger.info(f"Testing URL: {test_url}")
    
    logger.info("=" * 60)
    logger.info("Step 1: Getting video info...")
    logger.info("=" * 60)
    
    video_info = get_youtube_video_info(url=test_url)
    
    if video_info:
        logger.info(f"✓ Video info retrieved successfully!")
        logger.info(f"  Title: {video_info.get('title')}")
        logger.info(f"  Duration: {video_info.get('duration')} seconds")
        logger.info(f"  Uploader: {video_info.get('uploader')}")
    else:
        logger.error("✗ Failed to get video info")
        return
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 2: Downloading video...")
    logger.info("=" * 60)
    
    output_path = "./data/temp/test_age_restricted.mp4"
    
    success = await download_youtube_video(
        url=test_url,
        output_path=output_path,
        max_retries=2
    )
    
    if success:
        logger.info(f"✓ Download successful! File saved to: {output_path}")
        file_size = Path(output_path).stat().st_size
        logger.info(f"  File size: {file_size / 1024 / 1024:.2f} MB")
    else:
        logger.error("✗ Download failed")


if __name__ == "__main__":
    asyncio.run(test_age_restricted_video())

