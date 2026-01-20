#!/bin/bash
set -e

echo "=== Проверка Chrome профилей в Docker ==="
echo ""

echo "1. Список доступных профилей:"
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
from app.utils.video.youtube import get_chrome_profiles
profiles = get_chrome_profiles()
print(f'Найдено профилей: {len(profiles)}')
for i, profile in enumerate(profiles, 1):
    print(f'  {i}. {profile}')
"

echo -e "\n2. Тест каждого профиля с возрастным видео:"
docker-compose -f docker-compose.production.yml exec -T worker python3 -c "
from app.utils.video.youtube import get_chrome_profiles
import yt_dlp

profiles = get_chrome_profiles()
url = 'https://www.youtube.com/watch?v=0KE1ayhUYGY'

for profile in profiles:
    print(f'\n--- Тест профиля: {profile} ---')
    try:
        ydl_opts = {
            'quiet': False,
            'skip_download': True,
            'cookiesfrombrowser': ('chrome', profile),
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_unplugged'],
                    'player_skip': ['webpage'],
                }
            },
        }
        with yt_dlp.YoutubeDL(params=ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('title'):
                print(f'✓✓✓ РАБОТАЕТ с профилем {profile}!')
                print(f'   Название: {info.get(\"title\")}')
            else:
                print(f'✗ Профиль {profile}: не удалось получить информацию')
    except Exception as e:
        error_msg = str(e)
        if 'age' in error_msg.lower() or 'verify' in error_msg.lower():
            print(f'✗ Профиль {profile}: аккаунт не верифицирован по возрасту')
        else:
            print(f'✗ Профиль {profile}: {error_msg[:100]}')
"

echo -e "\n=== Проверка завершена ==="
echo ""
echo "Если все профили не работают, нужно:"
echo "1. Запустить VNC: docker-compose -f docker-compose.production.yml exec -d worker bash /app/start_vnc.sh"
echo "2. Подключиться к VNC (порт 5900)"
echo "3. Создать новый профиль Chrome с верифицированным аккаунтом"
echo "4. Убедиться, что Chrome запущен с флагом --password-store=basic"
