# Setup Chrome Profile for YouTube Age-Restricted Videos in Docker

## Проблема
YouTube age-restricted видео требуют авторизации. В Docker нужен Chrome профиль с активной сессией YouTube.

## Решение

### Вариант 1: Копирование Chrome профиля с локального Mac

1. На вашем Mac (где вы залогинены в YouTube):

```bash
cd ~/Projects/CutClipAI

# Создаем папку для Chrome профиля
mkdir -p ./data/chrome_profile/Default

# Копируем Cookies из Chrome
cp ~/Library/Application\ Support/Google/Chrome/Default/Cookies ./data/chrome_profile/Default/
```

2. Загрузите папку `./data/chrome_profile` на сервер:

```bash
# С локального Mac
scp -r ./data/chrome_profile root@your-server:~/CutClipAI/data/
```

3. На сервере перезапустите контейнеры:

```bash
cd ~/CutClipAI
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

### Вариант 2: Установка Chrome на сервере (НЕ в Docker)

1. Установите Chrome на Ubuntu сервере:

```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb
```

2. Установите X virtual framebuffer:

```bash
sudo apt-get install xvfb
```

3. Откройте Chrome и залогиньтесь:

```bash
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
google-chrome
```

4. Копируйте профиль в проект:

```bash
cd ~/CutClipAI
mkdir -p ./data/chrome_profile
cp -r ~/.config/google-chrome/* ./data/chrome_profile/
```

5. Перезапустите Docker:

```bash
docker-compose -f docker-compose.production.yml restart worker
```

### Проверка

```bash
# Проверяем что Chrome профиль виден в контейнере
docker-compose -f docker-compose.production.yml exec worker ls -la /root/.config/google-chrome/Default/

# Проверяем что yt-dlp видит профиль
docker-compose -f docker-compose.production.yml exec worker python3 -c "
from app.utils.video.youtube import get_chrome_profiles
print('Chrome profiles:', get_chrome_profiles())
"

# Тестируем age-restricted видео
docker-compose -f docker-compose.production.yml exec worker python3 test_youtube_age_restricted.py "https://www.youtube.com/watch?v=0KE1ayhUYGY"
```

## Важно

- Chrome профиль хранится в `./data/chrome_profile/` на хосте
- Монтируется в `/root/.config/google-chrome/` в контейнере
- Профиль сохраняется между перезапусками контейнера
- Нужно обновлять профиль, если YouTube сессия истекает (примерно раз в месяц)

## Troubleshooting

### yt-dlp не видит Chrome профиль

```bash
# Проверьте права доступа
sudo chmod -R 755 ./data/chrome_profile
```

### Ошибка "Could not find Chrome"

```bash
# Проверьте что Chrome установлен в Docker
docker-compose -f docker-compose.production.yml exec worker which google-chrome
```
