import re
import asyncio
import os
import subprocess
import shlex
from pathlib import Path
import yt_dlp
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

HOST_IP = os.getenv("DOCKER_HOST_IP", "172.17.0.1")

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
    Get all available Chrome profile names (macOS and Linux).
    """
    # Попробуем Linux путь (Docker/сервер)
    chrome_path = Path.home() / ".config/google-chrome"
    
    # Если не Linux, попробуем macOS
    if not chrome_path.exists():
        chrome_path = Path.home() / "Library/Application Support/Google/Chrome"
    
    profiles = []
    
    if chrome_path.exists():
        logger.info(f"Found Chrome directory: {chrome_path}")
        for item in chrome_path.iterdir():
            if item.is_dir() and (item.name.startswith("Profile ") or item.name == "Default"):
                # Проверяем что есть файл Cookies
                cookies_file = item / "Cookies"
                if cookies_file.exists():
                    profiles.append(item.name)
                    logger.info(f"Found Chrome profile with cookies: {item.name}")
    
    if not profiles:
        profiles = ["Default"]
        logger.warning(f"No Chrome profiles found, using Default")
    
    return sorted(list(set(profiles)), key=lambda x: (x != "Default", x))

def get_cookies_files() -> list[Path]:
    """
    Get all youtube cookies files from data directory.
    Returns sorted list of cookie file paths.
    """
    data_dir = Path("/app/data")
    cookies_files = []
    
    # Find all youtube_cookies*.txt files
    for file in data_dir.glob("youtube_cookies*.txt"):
        if file.is_file():
            cookies_files.append(file)
            logger.info(f"Found cookies file: {file.name}")
    
    return sorted(cookies_files)

async def download_via_host_ytdlp(
    url: str,
    output_path: str,
    profile: str = None,
) -> bool:
    """
    Download video using yt-dlp on HOST (not in Docker).
    This allows Chrome profile cookies to be decrypted via host keyring.
    """
    logger.info(f"Attempting download via HOST yt-dlp with profile: {profile}")
    
    cmd_base = f"yt-dlp --format bestvideo+bestaudio/best --output {shlex.quote(output_path)} --merge-output-format mp4 --no-check-certificate"
    
    if profile:
        cmd_base += f" --cookies-from-browser chrome:{profile}"
    
    cmd_base += f" {shlex.quote(url)}"
    
    cmd_parts = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=5",
        f"root@{HOST_IP}",
        cmd_base
    ]
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=300
            )
        )
        
        if result.returncode == 0:
            logger.info(f"HOST yt-dlp SUCCESS with profile {profile}")
            logger.debug(f"Output: {result.stdout}")
            return True
        else:
            logger.warning(f"HOST yt-dlp FAILED with profile {profile}")
            logger.warning(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"HOST yt-dlp timeout for profile {profile}")
        return False
    except Exception as e:
        logger.error(f"HOST yt-dlp exception: {e}")
        return False

async def download_youtube_video(
    url: str,
    output_path: str,
) -> bool:
    """
    Download video from YouTube using cookies files or Chrome profiles via yt-dlp.
    Priority: 1) Cookies files -> 2) Chrome profiles -> 3) No auth
    """
    
    # Try 1: Use cookies files (WORKS IN DOCKER)
    cookies_files = get_cookies_files()
    if cookies_files:
        logger.info(f"Found {len(cookies_files)} cookies files, trying each...")
        
        for cookies_file in cookies_files:
            logger.info(f"--- Attempting with cookies file: {cookies_file.name} ---")
            
            ydl_opts = {
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'outtmpl': output_path,
                'merge_output_format': 'mp4',
                'cookiefile': str(cookies_file),
                'ffmpeg_location': settings.FFMPEG_PATH,
                'nocheckcertificate': True,
                'quiet': False,
                'no_warnings': False,
                'age_limit': 21,
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            }
            
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: yt_dlp.YoutubeDL(ydl_opts).download([url])
                )
                
                if Path(output_path).exists():
                    logger.info(f"SUCCESS: Video downloaded using {cookies_file.name}")
                    return True
                
                if Path(str(output_path) + ".mp4").exists():
                    Path(str(output_path) + ".mp4").rename(output_path)
                    logger.info(f"SUCCESS: Video downloaded using {cookies_file.name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Cookies file {cookies_file.name} failed: {e}")
                continue
        
        logger.error(f"All {len(cookies_files)} cookies files failed")
    else:
        logger.warning("No cookies files found in /app/data/")
    
    # Try 2: Chrome profiles via HOST yt-dlp (can decrypt cookies via keyring!)
    profiles = get_chrome_profiles()
    if profiles:
        logger.info(f"Trying Chrome profiles via HOST yt-dlp: {profiles}")

        for profile in profiles:
            logger.info(f"--- Attempting with HOST profile: {profile} ---")
            
            try:
                success = await download_via_host_ytdlp(
                    url=url,
                    output_path=output_path,
                    profile=profile
                )
                
                if success and Path(output_path).exists():
                    logger.info(f"SUCCESS: Video downloaded using HOST profile {profile}")
                    return True
                    
            except Exception as e:
                logger.warning(f"HOST profile {profile} failed: {e}")
                continue
        
        logger.error("All HOST Chrome profiles failed")
    
    # Try 3: Without authentication (works for public videos)
    logger.info("--- Attempting without authentication ---")
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
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
            logger.info(f"SUCCESS: Video downloaded without authentication")
            return True
        
        if Path(str(output_path) + ".mp4").exists():
            Path(str(output_path) + ".mp4").rename(output_path)
            return True
            
    except Exception as e:
        logger.error(f"Download without authentication failed: {e}")
            
    logger.error("All download methods failed. Upload cookies files to /app/data/ or check video accessibility.")
    return False
