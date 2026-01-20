#!/bin/bash
set -e

echo "=== Проверка VNC ==="
echo ""

echo "1. Проверка процессов VNC в контейнере..."
docker-compose -f docker-compose.production.yml exec -T worker ps aux | grep -E "(Xvfb|x11vnc|fluxbox)" || echo "Процессы VNC не найдены"

echo -e "\n2. Проверка порта 5900 в контейнере..."
docker-compose -f docker-compose.production.yml exec -T worker netstat -tlnp 2>/dev/null | grep 5900 || echo "Порт 5900 не слушается"

echo -e "\n3. Проверка порта 5900 на хосте..."
netstat -tlnp 2>/dev/null | grep 5900 || echo "Порт 5900 не проброшен на хост"

echo -e "\n4. Попытка запуска VNC..."
docker-compose -f docker-compose.production.yml exec -T worker bash -c "
    export DISPLAY=:99
    pgrep Xvfb || Xvfb :99 -screen 0 1920x1080x24 &
    sleep 2
    pgrep fluxbox || fluxbox -display :99 &
    sleep 2
    pgrep x11vnc || x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -shared -bg
    sleep 2
    echo 'VNC процессы:'
    ps aux | grep -E '(Xvfb|x11vnc|fluxbox)' | grep -v grep
    echo ''
    echo 'Порт 5900:'
    netstat -tlnp 2>/dev/null | grep 5900 || echo 'Порт не слушается'
"

echo -e "\n=== Готово! ==="
echo ""
echo "Если VNC запущен, подключись через:"
echo "  ssh -L 5900:localhost:5900 root@45.135.234.33"
echo "  Затем VNC Viewer -> localhost:5900"
