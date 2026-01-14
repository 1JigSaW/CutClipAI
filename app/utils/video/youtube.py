import re
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

import yt_dlp

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


def get_chrome_profiles() -> List[str]:
    chrome_path_macos = Path.home() / "Library/Application Support/Google/Chrome"
    chrome_path_linux = Path.home() / ".config/google-chrome"
    
    chrome_path = chrome_path_macos if chrome_path_macos.exists() else chrome_path_linux
    
    profiles = []
    
    if chrome_path.exists():
        logger.info(f"Found Chrome directory: {chrome_path}")
        for item in chrome_path.iterdir():
            if item.is_dir() and (item.name.startswith("Profile ") or item.name == "Default"):
                cookies_paths = [
                    item / "Cookies",
                    item / "Network" / "Cookies",
                ]
                has_cookies = False
                for cookies_path in cookies_paths:
                    if cookies_path.exists():
                        has_cookies = True
                        break
                if has_cookies:
                    profiles.append(item.name)
                    logger.debug(f"Found Chrome profile: {item.name}")
    
    if not profiles:
        logger.debug("No Chrome profiles found")
    
    return sorted(list(set(profiles)), key=lambda x: (x != "Default", x))


class YouTubeDownloader:

    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_format_options(self) -> List[str]:
        return [
            'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba',
            'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'bestvideo+bestaudio/best',
            'best',
        ]

    def get_optimal_download_options(
        self,
        video_id: str,
        format_string: Optional[str] = None,
    ) -> Dict[str, Any]:
        output_path = self.temp_dir / f"{video_id}.%(ext)s"

        if format_string is None:
            format_string = self.get_format_options()[0]

        return {
            'outtmpl': str(output_path),
            'format': format_string,
            'merge_output_format': 'mp4',
            'writesubtitles': False,
            'writeautomaticsub': False,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'http_chunk_size': 10485760,
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'extract_flat': False,
            'writeinfojson': False,
            'nocheckcertificate': True,
            'prefer_insecure': False,
            'age_limit': None,
            'ffmpeg_location': settings.FFMPEG_PATH,
        }


def get_youtube_video_id(
    url: str,
) -> Optional[str]:
    if not isinstance(url, str) or not url.strip():
        return None

    url = url.strip()

    patterns = [
        r"(?:youtube\.com/(?:.*v=|v/|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/v/([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"m\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern=pattern, string=url, flags=re.IGNORECASE)
        if match:
            video_id = match.group(1)
            if len(video_id) == 11:
                return video_id

    try:
        parsed_url = urlparse(url=url)
        if 'youtube.com' in parsed_url.netloc.lower():
            query = parse_qs(qs=parsed_url.query)
            video_ids = query.get("v")
            if video_ids and len(video_ids[0]) == 11:
                return video_ids[0]
    except Exception as e:
        logger.warning(f"Error parsing URL query parameters: {e}")

    return None


def is_youtube_url(
    url: str,
) -> bool:
    video_id = get_youtube_video_id(url=url)
    return video_id is not None


def get_cookies_options() -> Optional[Dict[str, Any]]:
    chrome_profiles = get_chrome_profiles()
    cookies_file = Path(settings.TEMP_DIR).parent / "youtube_cookies.txt"
    
    if chrome_profiles:
        return {'cookiesfrombrowser': ('chrome', chrome_profiles[0])}
    elif cookies_file.exists():
        return {'cookiefile': str(cookies_file)}
    
    return None


def get_youtube_video_info(
    url: str,
) -> Optional[Dict[str, Any]]:
    video_id = get_youtube_video_id(url=url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {url}")
        return None

    chrome_profiles = get_chrome_profiles()
    cookies_file = Path(settings.TEMP_DIR).parent / "youtube_cookies.txt"
    
    methods_to_try = []
    
    if chrome_profiles:
        methods_to_try.extend([('chrome_profile', p) for p in chrome_profiles])
        logger.info(f"Found {len(chrome_profiles)} Chrome profiles")
    
    if cookies_file.exists():
        methods_to_try.append(('cookies_file', str(cookies_file)))
        logger.info(f"Found cookies file: {cookies_file}")
    
    if not methods_to_try:
        methods_to_try.append(('none', None))
        logger.info("No Chrome profiles or cookies file found, trying without authentication")
    
    for method_type, method_value in methods_to_try:
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'socket_timeout': 30,
                'nocheckcertificate': True,
                'extract_flat': False,
                'format': None,
            }
            
            if method_type == 'chrome_profile':
                ydl_opts['cookiesfrombrowser'] = ('chrome', method_value)
                logger.debug(f"Trying with Chrome profile: {method_value}")
            elif method_type == 'cookies_file':
                ydl_opts['cookiefile'] = method_value
                logger.debug(f"Trying with cookies file: {method_value}")
            else:
                logger.debug("Trying without authentication")
            
            with yt_dlp.YoutubeDL(params=ydl_opts) as ydl:
                ie = ydl.get_info_extractor('Youtube')
                ie.set_downloader(ydl)
                info = ie.extract(url)
                
                if info and info.get('title'):
                    if method_type == 'chrome_profile':
                        method_msg = f"with Chrome profile: {method_value}"
                    elif method_type == 'cookies_file':
                        method_msg = "with cookies file"
                    else:
                        method_msg = "without authentication"
                    
                    logger.info(f"✓ Successfully extracted info {method_msg}")
                    return {
                        'id': info.get('id'),
                        'title': info.get('title'),
                        'description': info.get('description', ''),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'upload_date': info.get('upload_date'),
                        'view_count': info.get('view_count'),
                        'like_count': info.get('like_count'),
                        'thumbnail': info.get('thumbnail'),
                        'format_id': info.get('format_id'),
                        'resolution': info.get('resolution'),
                        'fps': info.get('fps'),
                        'filesize': info.get('filesize'),
                    }
                    
        except Exception as e:
            error_msg = str(e)
            if method_type == 'chrome_profile':
                logger.debug(f"Chrome profile '{method_value}' failed: {error_msg[:200]}")
            elif method_type == 'cookies_file':
                logger.debug(f"Cookies file failed: {error_msg[:200]}")
            else:
                logger.debug(f"No authentication failed: {error_msg[:200]}")
            continue
    
    logger.error(f"All methods failed to extract video info (tried {len(methods_to_try)} methods)")
    return None


def get_youtube_video_title(
    url: str,
) -> Optional[str]:
    video_info = get_youtube_video_info(url=url)
    return video_info.get('title') if video_info else None


async def download_youtube_video(
    url: str,
    output_path: str,
    max_retries: int = 3,
) -> bool:
    logger.info(f"Starting YouTube download: {url}")

    video_id = get_youtube_video_id(url=url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return False

    downloader = YouTubeDownloader()

    loop = asyncio.get_event_loop()
    video_info = await loop.run_in_executor(
        None,
        lambda: get_youtube_video_info(url=url)
    )
    
    if not video_info:
        logger.error(f"Could not retrieve video information for: {url}")
        return False

    logger.info(f"Video: '{video_info.get('title')}' ({video_info.get('duration')}s)")

    duration = video_info.get('duration', 0)
    if duration > 3600:
        logger.warning(f"Video duration ({duration}s) exceeds recommended limit")

    format_options = downloader.get_format_options()
    
    for format_idx, format_string in enumerate(format_options):
        logger.info(f"Trying format {format_idx + 1}/{len(format_options)}: {format_string}")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Download attempt {attempt + 1}/{max_retries} with format: {format_string}")

                ydl_opts = downloader.get_optimal_download_options(
                    video_id=video_id,
                    format_string=format_string,
                )
                
                cookies_opts = get_cookies_options()
                if cookies_opts:
                    ydl_opts.update(cookies_opts)
                    logger.debug(f"Using cookies for download")

                def download_task():
                    with yt_dlp.YoutubeDL(params=ydl_opts) as ydl:
                        ydl.download(url_list=[url])

                await loop.run_in_executor(None, download_task)

                logger.info(f"Searching for downloaded file: {video_id}.*")
                for file_path in downloader.temp_dir.glob(f"{video_id}.*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mkv', '.webm']:
                        file_size = file_path.stat().st_size
                        logger.info(f"Download successful: {file_path.name} ({file_size // 1024 // 1024}MB)")
                        
                        output_path_obj = Path(output_path)
                        if file_path != output_path_obj:
                            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
                            file_path.rename(output_path_obj)
                            logger.info(f"Moved to: {output_path}")
                        
                return True

                logger.warning(f"No video file found after download attempt {attempt + 1}")

            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                
                if "Requested format is not available" in error_msg:
                    logger.warning(f"Format '{format_string}' not available, trying next format...")
                    break
                
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(delay=wait_time)
                else:
                    logger.warning(f"All retry attempts failed for format: {format_string}")
                    break

            except Exception as e:
                logger.error(f"Unexpected error during download attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(delay=wait_time)
                else:
                    logger.warning(f"All retry attempts failed for format: {format_string}")
                    break

    logger.info("Standard download failed, trying with Chrome profiles...")
    
    chrome_profiles = get_chrome_profiles()
    if not chrome_profiles:
        logger.warning("No Chrome profiles available")
        logger.error("All download methods failed (standard + no Chrome profiles)")
        return False
    
    logger.info(f"Found {len(chrome_profiles)} Chrome profiles")
    
    for profile in chrome_profiles:
        logger.info(f"Trying Chrome profile: {profile}")
        
        for format_string in format_options:
            try:
                logger.debug(f"Trying format with cookies: {format_string}")
                
                output_path_obj = Path(output_path)
                ydl_opts_cookies = {
                    'format': format_string,
                    'outtmpl': str(output_path_obj),
                    'merge_output_format': 'mp4',
                    'cookiesfrombrowser': ('chrome', profile),
                    'nocheckcertificate': True,
                    'quiet': True,
                    'no_warnings': False,
                    'socket_timeout': 30,
                    'retries': 3,
                    'fragment_retries': 3,
                    'ffmpeg_location': settings.FFMPEG_PATH,
                }
                
                def download_with_cookies():
                    with yt_dlp.YoutubeDL(params=ydl_opts_cookies) as ydl:
                        ydl.download(url_list=[url])
                
                await loop.run_in_executor(None, download_with_cookies)
                
                if output_path_obj.exists():
                    file_size = output_path_obj.stat().st_size
                    logger.info(f"Download successful with Chrome profile '{profile}' + format '{format_string}': ({file_size // 1024 // 1024}MB)")
                    return True
                
                for ext in ['.mp4', '.mkv', '.webm']:
                    test_path = Path(str(output_path_obj) + ext)
                    if test_path.exists():
                        if test_path != output_path_obj:
                            test_path.rename(output_path_obj)
                        file_size = output_path_obj.stat().st_size
                        logger.info(f"Download successful with Chrome profile '{profile}' + format '{format_string}': ({file_size // 1024 // 1024}MB)")
                    return True
                    
                logger.debug(f"No file found with format '{format_string}'")
                
            except Exception as e:
                error_msg = str(e)
                if "Requested format is not available" in error_msg:
                    logger.debug(f"Format '{format_string}' not available with profile '{profile}', trying next...")
                    continue
                else:
                    logger.warning(f"Chrome profile '{profile}' with format '{format_string}' failed: {e}")
                continue
        
        logger.warning(f"All formats failed with profile '{profile}'")
    
    logger.error(f"All download methods failed (standard + {len(chrome_profiles)} Chrome profiles)")
    return False


def get_video_duration(
    url: str,
) -> Optional[int]:
    video_info = get_youtube_video_info(url=url)
    return video_info.get('duration') if video_info else None


def is_video_suitable_for_processing(
    url: str,
    min_duration: int = 60,
    max_duration: int = 7200,
) -> bool:
    video_info = get_youtube_video_info(url=url)
    if not video_info:
        return False

    duration = video_info.get('duration', 0)

    if duration < min_duration or duration > max_duration:
        logger.warning(f"Video duration {duration}s outside allowed range ({min_duration}-{max_duration}s)")
        return False

    return True


def cleanup_downloaded_files(
    video_id: str,
):
    temp_dir = Path(settings.TEMP_DIR)

    for file_path in temp_dir.glob(f"{video_id}.*"):
        try:
            if file_path.is_file():
                file_path.unlink()
                logger.info(f"Cleaned up: {file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path.name}: {e}")
