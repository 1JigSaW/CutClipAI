#!/bin/bash
set -e

echo "=== Быстрое исправление Docker кеша ==="
echo ""

echo "1. Остановка всех контейнеров..."
docker-compose -f docker-compose.production.yml down || true

echo -e "\n2. Удаление старого контейнера worker..."
docker rm -f cutclipai_worker 2>/dev/null || true
docker rm -f $(docker ps -aq --filter "name=cutclipai_worker") 2>/dev/null || true

echo -e "\n3. Удаление только старых контейнеров (не образов)..."
docker container prune -f || true

echo -e "\n4. Пересборка worker с кешем (быстро)..."
docker-compose -f docker-compose.production.yml build worker

echo -e "\n5. Запуск контейнеров..."
docker-compose -f docker-compose.production.yml up -d

echo -e "\n6. Ожидание запуска (10 секунд)..."
sleep 10

echo -e "\n7. Проверка статуса контейнеров..."
docker-compose -f docker-compose.production.yml ps

echo -e "\n=== Готово! ==="
