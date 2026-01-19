#!/bin/bash
set -e

echo "=== Деплой фикса для YouTube issue #15569 ==="
echo ""

SERVER="root@45.135.234.33"
PROJECT_DIR="CutClipAI"

echo "1. Коммит изменений..."
git add -A
git commit -m "Fix YouTube age-restricted videos (issue #15569): update yt-dlp and use android_unplugged client" || echo "Нет изменений для коммита"

echo -e "\n2. Push на GitHub..."
git push origin main

echo -e "\n3. Pull на сервере..."
ssh $SERVER "cd $PROJECT_DIR && git pull origin main"

echo -e "\n4. Пересборка Docker контейнера..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose -f docker-compose.production.yml build --no-cache worker"

echo -e "\n5. Перезапуск контейнеров..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose -f docker-compose.production.yml down && docker-compose -f docker-compose.production.yml up -d"

echo -e "\n6. Ожидание запуска (15 секунд)..."
sleep 15

echo -e "\n7. Проверка версии yt-dlp..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose -f docker-compose.production.yml exec -T worker python3 -c 'import yt_dlp; print(f\"yt-dlp: {yt_dlp.version.__version__}\")'"

echo -e "\n8. Тест возрастного видео..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose -f docker-compose.production.yml exec -T worker python3 -c \"
from app.utils.video.youtube import get_youtube_video_info
info = get_youtube_video_info('https://www.youtube.com/watch?v=0KE1ayhUYGY')
if info:
    print(f'✓✓✓ РАБОТАЕТ! Название: {info.get(\\\"title\\\")}')
else:
    print('✗ Не работает')
\""

echo -e "\n=== Деплой завершен ==="
