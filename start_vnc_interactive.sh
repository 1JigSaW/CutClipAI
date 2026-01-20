#!/bin/bash

echo "=== Запуск VNC в интерактивном режиме ==="
echo ""
echo "Этот скрипт запустит VNC и будет ждать подключения"
echo "Для выхода нажми Ctrl+C"
echo ""

docker-compose -f docker-compose.production.yml exec worker bash /app/start_vnc.sh
