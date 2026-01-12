# Деплой с поддержкой Age-Restricted видео

## Быстрый старт

### Шаг 1: Копируем Chrome профиль с вашего Mac

```bash
# На локальном Mac (где вы залогинены в YouTube)
cd ~/Projects/CutClipAI

# Создаем папку для Chrome профиля
mkdir -p ./data/chrome_profile/Default

# Копируем Cookies из вашего Chrome
cp ~/Library/Application\ Support/Google/Chrome/Default/Cookies ./data/chrome_profile/Default/

# Копируем на сервер
scp -r ./data/chrome_profile root@your-server-ip:~/CutClipAI/data/
```

### Шаг 2: На сервере

```bash
ssh root@your-server-ip

cd ~/CutClipAI

# Получаем последние изменения
git pull

# Пересобираем Docker (Chrome теперь включен)
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Ждем пока все запустится (30-60 секунд)
sleep 60
```

### Шаг 3: Проверяем

```bash
# Проверяем что Chrome профиль виден
docker-compose -f docker-compose.production.yml exec worker ls -la /root/.config/google-chrome/Default/Cookies

# Проверяем что yt-dlp находит профили
docker-compose -f docker-compose.production.yml exec worker python3 -c "
from app.utils.video.youtube import get_chrome_profiles
profiles = get_chrome_profiles()
print(f'Found {len(profiles)} Chrome profiles: {profiles}')
"

# Тестируем age-restricted видео
docker-compose -f docker-compose.production.yml exec worker python3 test_youtube_age_restricted.py "https://www.youtube.com/watch?v=0KE1ayhUYGY"
```

## Что изменилось

1. ✅ Chrome установлен в Docker контейнер
2. ✅ Chrome профиль монтируется из `./data/chrome_profile/`
3. ✅ yt-dlp использует Chrome cookies через `cookiesfrombrowser('chrome')`
4. ✅ Age-restricted видео теперь работают

## Обновление профиля

YouTube сессия может истекать. Если перестанет работать (~раз в месяц):

```bash
# На Mac повторите Шаг 1
# Скопируйте свежие Cookies на сервер
# Перезапустите worker

docker-compose -f docker-compose.production.yml restart worker
```

## Troubleshooting

### "No Chrome profiles found"

```bash
# Проверьте что папка существует
ls -la ~/CutClipAI/data/chrome_profile/Default/

# Проверьте права
chmod -R 755 ~/CutClipAI/data/chrome_profile/
```

### "Could not find Chrome"

```bash
# Проверьте что Chrome установлен
docker-compose -f docker-compose.production.yml exec worker google-chrome --version
```

### Ошибка "Sign in to confirm your age" все еще появляется

```bash
# Cookies устарели, обновите профиль (Шаг 1)
# ИЛИ ваш YouTube аккаунт не может смотреть age-restricted видео
```

