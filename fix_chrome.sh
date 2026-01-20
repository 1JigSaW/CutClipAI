#!/bin/bash
set -e

echo "=== Исправление Chrome ==="
echo ""

docker-compose -f docker-compose.production.yml exec worker bash -c "
    echo '1. Убиваем все процессы Chrome...'
    pkill -9 -f google-chrome || true
    sleep 2
    
    echo ''
    echo '2. Проверяем, что Chrome убит...'
    if pgrep -f 'google-chrome' > /dev/null; then
        echo '  ✗ Chrome все еще запущен, принудительно убиваем...'
        pkill -9 -f google-chrome
        sleep 1
    else
        echo '  ✓ Chrome не запущен'
    fi
    
    echo ''
    echo '3. Проверяем VNC...'
    export DISPLAY=:99
    if ! pgrep -f 'Xvfb :99' > /dev/null; then
        echo '  ✗ Xvfb не запущен, запускаем...'
        Xvfb :99 -screen 0 1920x1080x24 &
        sleep 3
    else
        echo '  ✓ Xvfb запущен'
    fi
    
    echo ''
    echo '4. Инициализируем keyring...'
    export \$(dbus-launch 2>/dev/null) || true
    echo -n '' | gnome-keyring-daemon --unlock --components=secrets 2>/dev/null || true
    
    echo ''
    echo '5. Запускаем Chrome...'
    DISPLAY=:99 google-chrome --no-sandbox --disable-dev-shm-usage --password-store=basic --user-data-dir=/root/.config/google-chrome > /tmp/chrome.log 2>&1 &
    CHROME_PID=\$!
    sleep 5
    
    echo ''
    echo '6. Проверяем Chrome...'
    if ps -p \$CHROME_PID > /dev/null 2>&1 || pgrep -f 'google-chrome' > /dev/null; then
        echo '  ✓ Chrome запущен!'
        echo '  PID: ' \$(pgrep -f 'google-chrome' | head -1)
        echo '  Процессы:'
        ps aux | grep google-chrome | grep -v grep | head -3
    else
        echo '  ✗ Chrome не запустился'
        echo '  Логи:'
        tail -50 /tmp/chrome.log 2>/dev/null || echo '  Логи не найдены'
    fi
"

echo ""
echo "=== Готово! ==="
