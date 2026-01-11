import asyncio
from pathlib import Path
from typing import Optional
from apify_client import ApifyClient
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ApifyYouTubeDownloader:
    
    def __init__(self):
        self.client = None
        if hasattr(settings, 'APIFY_API_TOKEN') and settings.APIFY_API_TOKEN:
            self.client = ApifyClient(settings.APIFY_API_TOKEN)
            logger.info("✅ Apify client initialized")
        else:
            logger.warning("⚠️ APIFY_API_TOKEN not set, Apify downloader disabled")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    async def download_video(
        self,
        url: str,
        output_path: str,
    ) -> bool:
        if not self.is_available():
            logger.error("❌ Apify client not available")
            return False
        
        try:
            logger.info(f"🚀 Starting Apify download for: {url}")
            
            run_input = {
                "startUrls": [url],
                "maxResults": 1,
                "maxResultsShorts": 0,
                "maxResultStreams": 0,
                "downloadSubtitles": False,
                "subtitlesFormat": "srt",
            }
            
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.client.actor("h7sDV53CddomktSi5").call(run_input=run_input)
            )
            
            logger.info(f"📊 Apify run completed: {run.get('id')}")
            
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.error("❌ No dataset returned from Apify")
                return False
            
            items = await loop.run_in_executor(
                None,
                lambda: list(self.client.dataset(dataset_id).iterate_items())
            )
            
            if not items:
                logger.error("❌ No items in Apify dataset")
                return False
            
            video_item = items[0]
            logger.info(f"📹 Video info: {video_item.get('title', 'Unknown')}")
            
            video_url = video_item.get('videoUrl') or video_item.get('url')
            if not video_url:
                logger.error("❌ No video URL in Apify response")
                logger.debug(f"Available keys: {list(video_item.keys())}")
                return False
            
            logger.info(f"⬇️ Downloading from: {video_url}")
            
            import httpx
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(video_url)
                response.raise_for_status()
                
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
            
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"✅ Apify download SUCCESS: {file_size / 1024 / 1024:.2f} MB")
                return True
            else:
                logger.error("❌ File not created after Apify download")
                return False
                
        except Exception as e:
            logger.error(f"💥 Apify download failed: {e}")
            logger.exception(e)
            return False


apify_downloader = ApifyYouTubeDownloader()

