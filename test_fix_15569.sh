#!/bin/bash
set -e

echo "=== YouTube Age-Restricted Video Test (Issue #15569 Fix) ==="
echo ""

echo "1. Проверка версии yt-dlp..."
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
import yt_dlp
print(f'yt-dlp version: {yt_dlp.version.__version__}')
"

echo -e "\n2. Проверка настроек extractor_args..."
docker-compose -f docker-compose.production.yml exec -T worker grep -A 5 "extractor_args" /app/app/utils/video/youtube.py | head -15

echo -e "\n3. Тест возрастного видео (0KE1ayhUYGY)..."
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
from app.utils.video.youtube import get_youtube_video_info

url = 'https://www.youtube.com/watch?v=0KE1ayhUYGY'
print(f'\nПопытка получить информацию: {url}')

info = get_youtube_video_info(url)

if info:
    print(f'\n✓✓✓ УСПЕХ!')
    print(f'Название: {info.get(\"title\")}')
    print(f'Длительность: {info.get(\"duration\")}s')
    print(f'Описание: {info.get(\"description\", \"\")[:100]}...')
else:
    print('\n✗ ОШИБКА: Не удалось получить информацию о видео')
"

echo -e "\n4. Тест обычного видео (dQw4w9WgXcQ)..."
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
from app.utils.video.youtube import get_youtube_video_info

url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
info = get_youtube_video_info(url)

if info:
    print(f'✓ Обычное видео работает: {info.get(\"title\")}')
else:
    print('✗ Ошибка с обычным видео')
"

echo -e "\n=== Тест завершен ==="
