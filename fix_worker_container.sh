#!/bin/bash
set -e

echo "=== Исправление контейнера worker ==="
echo ""

echo "1. Остановка и удаление старого контейнера worker..."
docker-compose -f docker-compose.production.yml stop worker || true
docker rm -f cutclipai_worker 2>/dev/null || true

echo -e "\n2. Пересборка worker..."
docker-compose -f docker-compose.production.yml build worker

echo -e "\n3. Запуск worker..."
docker-compose -f docker-compose.production.yml up -d worker

echo -e "\n4. Ожидание запуска (5 секунд)..."
sleep 5

echo -e "\n5. Проверка статуса..."
docker-compose -f docker-compose.production.yml ps worker

echo -e "\n=== Готово! ==="
