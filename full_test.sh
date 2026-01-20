#!/bin/bash
set -e

echo "============================================================"
echo "  ПОЛНАЯ ПРОВЕРКА YOUTUBE API"
echo "============================================================"
echo ""

TEST_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

echo "Шаг 1: Проверка .env файла..."
if grep -q "YOUTUBE_DOWNLOAD_API_URL" .env 2>/dev/null; then
    API_URL=$(grep "YOUTUBE_DOWNLOAD_API_URL" .env | head -1 | cut -d'=' -f2)
    echo "✓ Найдено: YOUTUBE_DOWNLOAD_API_URL=$API_URL"
else
    echo "✗ Переменная не найдена в .env"
    echo "  Добавь: YOUTUBE_DOWNLOAD_API_URL=https://d81vybws970pyx-8001.proxy.runpod.net"
    exit 1
fi

echo ""
echo "Шаг 2: Проверка worker контейнера..."
if ! docker-compose -f docker-compose.production.yml ps worker | grep -q "Up"; then
    echo "✗ Worker контейнер не запущен"
    echo "  Запусти: docker-compose -f docker-compose.production.yml up -d worker"
    exit 1
else
    echo "✓ Worker контейнер запущен"
fi

echo ""
echo "Шаг 3: Проверка переменной в контейнере..."
CONTAINER_API_URL=$(docker-compose -f docker-compose.production.yml exec -T worker python3 -c "from app.core.config import settings; print(settings.YOUTUBE_DOWNLOAD_API_URL or 'NOT_SET')" 2>/dev/null || echo "ERROR")

if [ "$CONTAINER_API_URL" = "NOT_SET" ] || [ "$CONTAINER_API_URL" = "ERROR" ]; then
    echo "✗ Переменная не загружена в контейнер"
    echo "  Перезапусти worker: docker-compose -f docker-compose.production.yml restart worker"
    exit 1
else
    echo "✓ Переменная загружена: $CONTAINER_API_URL"
fi

echo ""
echo "Шаг 4: Тест API через curl (быстрая проверка)..."
curl -X POST "$CONTAINER_API_URL/api/download-video/" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$TEST_URL\"}" \
  --output /tmp/test_curl.mp4 \
  --max-time 30 \
  --silent \
  --write-out "\nHTTP Status: %{http_code}\n" \
  --fail-with-body > /dev/null 2>&1 || CURL_ERROR=$?

if [ -f /tmp/test_curl.mp4 ] && [ -s /tmp/test_curl.mp4 ]; then
    SIZE=$(stat -f%z /tmp/test_curl.mp4 2>/dev/null || stat -c%s /tmp/test_curl.mp4 2>/dev/null)
    echo "✓ API работает! Размер файла: $((SIZE / 1024 / 1024)) MB"
    rm -f /tmp/test_curl.mp4
else
    echo "✗ API не отвечает или вернул ошибку"
    if [ -n "$CURL_ERROR" ]; then
        echo "  Код ошибки: $CURL_ERROR"
    fi
fi

echo ""
echo "Шаг 5: Тест через Python функцию..."
docker-compose -f docker-compose.production.yml exec -T worker python3 << 'PYTHON_SCRIPT'
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from app.utils.video.youtube import download_youtube_video
from app.core.config import settings

async def test():
    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    print(f'API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or "НЕ НАСТРОЕН"}')
    
    output_path = '/app/data/test_output/test_full.mp4'
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    success = await download_youtube_video(url=url, output_path=output_path, max_retries=2)
    
    if success and Path(output_path).exists():
        size = Path(output_path).stat().st_size
        print(f'✓ УСПЕХ! Размер: {size / 1024 / 1024:.2f} MB')
        return True
    else:
        print('✗ ОШИБКА: Загрузка не удалась')
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
PYTHON_SCRIPT

PYTHON_RESULT=$?

echo ""
echo "============================================================"
if [ $PYTHON_RESULT -eq 0 ]; then
    echo "  ✓✓✓ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!"
    echo "============================================================"
    echo ""
    echo "API работает корректно! Можно использовать."
else
    echo "  ✗ ОШИБКА В ТЕСТАХ"
    echo "============================================================"
    echo ""
    echo "Проверь логи:"
    echo "  docker-compose -f docker-compose.production.yml logs worker | tail -50"
    exit 1
fi
