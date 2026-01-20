#!/bin/bash
set -e

echo "=== Проверка конфигурации YouTube API ==="
echo ""

echo "1. Проверка переменной в .env файле..."
if grep -q "YOUTUBE_DOWNLOAD_API_URL" .env 2>/dev/null; then
    echo "✓ Переменная найдена в .env:"
    grep "YOUTUBE_DOWNLOAD_API_URL" .env | head -1
else
    echo "✗ Переменная не найдена в .env"
fi

echo ""
echo "2. Проверка переменной в Docker контейнере..."
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
from app.core.config import settings
api_url = settings.YOUTUBE_DOWNLOAD_API_URL
if api_url:
    print(f'✓ YOUTUBE_DOWNLOAD_API_URL настроен: {api_url}')
else:
    print('✗ YOUTUBE_DOWNLOAD_API_URL не настроен (будет использован yt-dlp)')
" 2>/dev/null || echo "✗ Не удалось проверить (контейнер не запущен?)"

echo ""
echo "3. Если переменная не загружена, перезапусти worker:"
echo "   docker-compose -f docker-compose.production.yml restart worker"
echo ""
echo "=== Готово! ==="
