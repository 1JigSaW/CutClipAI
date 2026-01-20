#!/bin/bash
set -e

echo "=== Запуск Chrome вручную ==="
echo ""

docker-compose -f docker-compose.production.yml exec worker bash -c "
    export DISPLAY=:99
    export \$(dbus-launch 2>/dev/null) || true
    echo -n '' | gnome-keyring-daemon --unlock --components=secrets 2>/dev/null || true
    
    if pgrep -f 'google-chrome' > /dev/null; then
        echo 'Chrome уже запущен'
        ps aux | grep google-chrome | grep -v grep
    else
        echo 'Запуск Chrome...'
        DISPLAY=:99 google-chrome --no-sandbox --disable-dev-shm-usage --password-store=basic --user-data-dir=/root/.config/google-chrome > /tmp/chrome.log 2>&1 &
        sleep 3
        
        if pgrep -f 'google-chrome' > /dev/null; then
            echo '✓ Chrome запущен успешно!'
            echo '  PID: ' \$(pgrep -f 'google-chrome' | head -1)
        else
            echo '✗ Chrome не запустился. Логи:'
            tail -30 /tmp/chrome.log 2>/dev/null || echo 'Логи не найдены'
        fi
    fi
"

echo ""
echo "=== Готово! ==="
echo ""
echo "Если Chrome запущен, подключись к VNC и открой Chrome"
