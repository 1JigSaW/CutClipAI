#!/bin/bash
set -e

echo "=== Настройка нового Chrome профиля с другим аккаунтом ==="
echo ""

echo "1. Запуск VNC сервера..."
docker-compose -f docker-compose.production.yml exec -d worker bash /app/start_vnc.sh

echo -e "\n2. Ожидание запуска VNC (5 секунд)..."
sleep 5

echo -e "\n3. Инструкции для подключения:"
echo ""
echo "   На твоем Mac выполни:"
echo "   ssh -L 5900:localhost:5900 root@45.135.234.33"
echo ""
echo "   Затем открой VNC Viewer и подключись к: localhost:5900"
echo ""
echo "   В Chrome:"
echo "   1. Открой chrome://settings/people"
echo "   2. Нажми 'Добавить' (Add person)"
echo "   3. Создай новый профиль (например, 'Profile 1')"
echo "   4. В новом окне Chrome открой youtube.com"
echo "   5. Залогинься в аккаунт с ВЕРИФИЦИРОВАННЫМ возрастом"
echo "   6. Открой возрастное видео для проверки"
echo "   7. Закрой Chrome"
echo ""
echo "4. После настройки профиля, проверь его:"
echo "   ./check_chrome_profiles.sh"
echo ""
echo "=== Готово! ==="
