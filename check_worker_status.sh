#!/bin/bash

echo "=== 🔍 Проверка статуса worker'а ==="
echo ""

echo "1️⃣ Статус всех контейнеров:"
docker-compose -f docker-compose.production.yml ps
echo ""

echo "2️⃣ Последние 100 строк логов worker'а:"
docker-compose -f docker-compose.production.yml logs --tail=100 worker
echo ""

echo "3️⃣ Ошибки в логах worker'а:"
docker-compose -f docker-compose.production.yml logs worker 2>&1 | grep -i "error\|exception\|failed\|traceback\|hang\|freeze" | tail -30
echo ""

echo "4️⃣ Логи по субтитрам и шрифтам:"
docker-compose -f docker-compose.production.yml logs worker 2>&1 | grep -i "subtitle\|font\|arial\|liberation" | tail -20
echo ""

echo "5️⃣ Активные задачи Celery:"
docker-compose -f docker-compose.production.yml exec worker celery -A app.core.celery_app inspect active 2>/dev/null || echo "Не удалось получить статус задач"
echo ""

echo "6️⃣ Использование ресурсов worker'а:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose -f docker-compose.production.yml ps -q worker) 2>/dev/null || echo "Worker не запущен"
echo ""

echo "=== 📝 Для просмотра логов в реальном времени: ==="
echo "docker-compose -f docker-compose.production.yml logs -f worker"
echo ""
echo "=== 🔄 Для перезапуска worker'а: ==="
echo "docker-compose -f docker-compose.production.yml restart worker"
