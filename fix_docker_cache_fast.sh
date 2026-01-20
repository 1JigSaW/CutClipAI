#!/bin/bash
set -e

echo "=== Быстрое исправление Docker кеша ==="
echo ""

echo "1. Остановка всех контейнеров..."
docker-compose -f docker-compose.production.yml down || true

echo -e "\n2. Удаление только старых контейнеров (не образов)..."
docker container prune -f || true

echo -e "\n3. Пересборка worker с кешем (быстро)..."
docker-compose -f docker-compose.production.yml build worker

echo -e "\n4. Запуск контейнеров..."
docker-compose -f docker-compose.production.yml up -d

echo -e "\n5. Ожидание запуска (10 секунд)..."
sleep 10

echo -e "\n6. Проверка статуса контейнеров..."
docker-compose -f docker-compose.production.yml ps

echo -e "\n=== Готово! ==="
