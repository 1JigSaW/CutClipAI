import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.utils.video.youtube import download_youtube_video
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


async def test_youtube_api_download():
    if len(sys.argv) > 1:
        test_url = sys.argv[1].strip()
    else:
        test_url = input("Введите URL YouTube видео: ").strip()
    
    if not test_url:
        logger.error("URL не введен")
        logger.info("Usage: python test_youtube_api.py <youtube_url>")
        return
    
    logger.info("=" * 60)
    logger.info("Тест загрузки YouTube видео через внешний API")
    logger.info("=" * 60)
    logger.info(f"URL: {test_url}")
    logger.info(f"API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or 'Не настроен (будет использован yt-dlp)'}")
    logger.info("")
    
    output_path = "./data/test_output/test_api_download.mp4"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Начинаю загрузку в: {output_path}")
    logger.info("")
    
    try:
        success = await download_youtube_video(
            url=test_url,
            output_path=output_path,
            max_retries=2
        )
        
        if success:
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info("")
                logger.info("=" * 60)
                logger.info("✓✓✓ УСПЕХ!")
                logger.info("=" * 60)
                logger.info(f"Файл сохранен: {output_path}")
                logger.info(f"Размер файла: {file_size / 1024 / 1024:.2f} MB")
                logger.info("")
            else:
                logger.error("✗ Файл не найден после загрузки")
        else:
            logger.error("")
            logger.error("=" * 60)
            logger.error("✗ ОШИБКА: Загрузка не удалась")
            logger.error("=" * 60)
            logger.error("")
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_youtube_api_download())
