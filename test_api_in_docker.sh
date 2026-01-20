#!/bin/bash
set -e

TEST_URL="${1:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"

echo "=== Тест YouTube API в Docker ==="
echo ""
echo "Video URL: $TEST_URL"
echo ""

echo "Способ 1: Копируем тестовый скрипт в контейнер..."
docker-compose -f docker-compose.production.yml cp test_youtube_api.py worker:/app/test_youtube_api.py

echo ""
echo "Способ 2: Запускаем тест напрямую через Python..."
docker-compose -f docker-compose.production.yml exec worker python3 -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from app.utils.video.youtube import download_youtube_video
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

async def test():
    url = '$TEST_URL'
    logger.info(f'Testing URL: {url}')
    logger.info(f'API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or \"Not configured (will use yt-dlp)\"}')
    
    output_path = '/app/data/test_output/test_api.mp4'
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    success = await download_youtube_video(url=url, output_path=output_path, max_retries=2)
    
    if success and Path(output_path).exists():
        file_size = Path(output_path).stat().st_size
        print(f'\n✓✓✓ SUCCESS!')
        print(f'File: {output_path}')
        print(f'Size: {file_size / 1024 / 1024:.2f} MB')
    else:
        print('\n✗ FAILED')

asyncio.run(test())
"

echo ""
echo "=== Готово! ==="
