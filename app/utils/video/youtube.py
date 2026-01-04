import re
import asyncio
import os
from pathlib import Path
import yt_dlp
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)

def is_youtube_url(url: str) -> bool:
    """
    Check if a string is a YouTube URL.
    """
    return bool(YOUTUBE_REGEX.match(url))

def get_chrome_profiles() -> list[str]:
    """
    Get all available Chrome profile names on macOS.
    """
    chrome_path = Path.home() / "Library/Application Support/Google/Chrome"
    profiles = ["Default"]
    
    if chrome_path.exists():
        for item in chrome_path.iterdir():
            if item.is_dir() and (item.name.startswith("Profile ") or item.name == "Default"):
                profiles.append(item.name)
    
    return sorted(list(set(profiles)), key=lambda x: (x != "Default", x))

async def download_youtube_video(
    url: str,
    output_path: str,
) -> bool:
    """
    Download video from YouTube using Chrome profiles via yt-dlp.
    """
    profiles = get_chrome_profiles()
    logger.info(f"Using Chrome profiles to download: {profiles}")

    for profile in profiles:
        logger.info(f"--- Attempting with profile: {profile} ---")
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'cookiesfrombrowser': ('chrome', profile),
            'ffmpeg_location': settings.FFMPEG_PATH,
            'nocheckcertificate': True,
            'quiet': False,
            'no_warnings': False,
        }
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).download([url])
            )
            
            if Path(output_path).exists():
                logger.info(f"SUCCESS: Video downloaded using profile {profile}")
                return True
            
            # Check for mp4 extension auto-append
            if Path(str(output_path) + ".mp4").exists():
                Path(str(output_path) + ".mp4").rename(output_path)
                return True
                
        except Exception as e:
            logger.warning(f"Profile {profile} failed: {e}")
            continue
            
    logger.error("All Chrome profiles failed. Check if you are logged in to YouTube in Chrome.")
    return False
