#!/bin/bash
set -e

echo "=== Проверка Chrome ==="
echo ""

echo "1. Проверка процессов Chrome в контейнере..."
docker-compose -f docker-compose.production.yml exec -T worker ps aux | grep -i chrome | grep -v grep || echo "Chrome не запущен"

echo -e "\n2. Проверка VNC процессов..."
docker-compose -f docker-compose.production.yml exec -T worker ps aux | grep -E "(Xvfb|x11vnc|fluxbox)" | grep -v grep || echo "VNC процессы не найдены"

echo -e "\n3. Попытка запуска Chrome вручную..."
docker-compose -f docker-compose.production.yml exec -T worker bash -c "
    export DISPLAY=:99
    export \$(dbus-launch 2>/dev/null) || true
    echo -n '' | gnome-keyring-daemon --unlock --components=secrets 2>/dev/null || true
    
    if ! pgrep -f 'google-chrome' > /dev/null; then
        echo 'Запуск Chrome...'
        DISPLAY=:99 google-chrome --no-sandbox --disable-dev-shm-usage --password-store=basic --user-data-dir=/root/.config/google-chrome > /tmp/chrome.log 2>&1 &
        sleep 3
        if pgrep -f 'google-chrome' > /dev/null; then
            echo '✓ Chrome запущен'
        else
            echo '✗ Chrome не запустился. Проверь логи:'
            tail -20 /tmp/chrome.log 2>/dev/null || echo 'Логи не найдены'
        fi
    else
        echo 'Chrome уже запущен'
    fi
"

echo -e "\n=== Готово! ==="
