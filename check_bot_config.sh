#!/bin/bash
set -e

echo "=== Проверка конфигурации Bot ==="
echo ""

echo "1. Проверка переменной в контейнере bot..."
docker-compose -f docker-compose.production.yml exec -T bot python3 -c "from app.core.config import settings; print(f'API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or \"НЕ НАСТРОЕН\"}')" 2>/dev/null || echo "✗ Не удалось проверить (контейнер не запущен?)"

echo ""
echo "2. Последние логи bot (YouTube):"
docker-compose -f docker-compose.production.yml logs bot | grep -i "youtube\|download\|api" | tail -20 || echo "Логи не найдены"

echo ""
echo "3. Если переменная не загружена, перезапусти bot:"
echo "   docker-compose -f docker-compose.production.yml restart bot"
echo ""
echo "=== Готово! ==="
