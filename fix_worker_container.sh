#!/bin/bash
set -e

echo "=== Исправление контейнера worker ==="
echo ""

echo "1. Остановка всех контейнеров..."
docker-compose -f docker-compose.production.yml stop || true

echo "2. Удаление всех контейнеров..."
docker-compose -f docker-compose.production.yml rm -f || true

echo "3. Удаление старых контейнеров вручную..."
docker rm -f cutclipai_worker cutclipai_api 2>/dev/null || true
docker rm -f $(docker ps -aq --filter "name=cutclipai") 2>/dev/null || true

echo -e "\n4. Пересборка worker..."
docker-compose -f docker-compose.production.yml build worker

echo -e "\n5. Запуск всех сервисов..."
docker-compose -f docker-compose.production.yml up -d

echo -e "\n6. Ожидание запуска (10 секунд)..."
sleep 10

echo -e "\n7. Проверка статуса..."
docker-compose -f docker-compose.production.yml ps

echo -e "\n=== Готово! ==="
