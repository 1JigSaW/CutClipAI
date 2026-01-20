#!/bin/bash
set -e

echo "=== Исправление Docker кеша ==="
echo ""

echo "1. Остановка всех контейнеров..."
docker-compose -f docker-compose.production.yml down || true

echo -e "\n2. Удаление старых контейнеров..."
docker container prune -f || true

echo -e "\n3. Удаление старых образов..."
docker image prune -a -f || true

echo -e "\n4. Пересборка worker без кеша..."
docker-compose -f docker-compose.production.yml build --no-cache worker

echo -e "\n5. Запуск контейнеров..."
docker-compose -f docker-compose.production.yml up -d

echo -e "\n6. Ожидание запуска (10 секунд)..."
sleep 10

echo -e "\n7. Проверка статуса контейнеров..."
docker-compose -f docker-compose.production.yml ps

echo -e "\n=== Готово! ==="
