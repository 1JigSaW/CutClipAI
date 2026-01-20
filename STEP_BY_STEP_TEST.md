# Пошаговая проверка YouTube API

## Шаг 1: Проверка переменной в .env

```bash
cd ~/CutClipAI
cat .env | grep YOUTUBE_DOWNLOAD_API_URL
```

**Должно быть:**
```
YOUTUBE_DOWNLOAD_API_URL=https://d81vybws970pyx-8001.proxy.runpod.net
```

**Если нет - добавь:**
```bash
echo "YOUTUBE_DOWNLOAD_API_URL=https://d81vybws970pyx-8001.proxy.runpod.net" >> .env
```

---

## Шаг 2: Проверка переменной в docker-compose.production.yml

```bash
cat docker-compose.production.yml | grep -A 5 "worker:" | grep -A 10 "environment:"
```

**Если переменной нет в environment, добавь в docker-compose.production.yml:**

Найди секцию `worker:` и добавь в `environment:`:

```yaml
worker:
  environment:
    YOUTUBE_DOWNLOAD_API_URL: ${YOUTUBE_DOWNLOAD_API_URL}
    # ... остальные переменные
```

---

## Шаг 3: Перезапуск worker

```bash
docker-compose -f docker-compose.production.yml restart worker
```

Подожди 5 секунд:
```bash
sleep 5
```

---

## Шаг 4: Проверка, что переменная загружена в контейнер

```bash
docker-compose -f docker-compose.production.yml exec worker python3 -c "from app.core.config import settings; print(f'API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or \"НЕ НАСТРОЕН\"}')"
```

**Должно вывести:**
```
API URL: https://d81vybws970pyx-8001.proxy.runpod.net
```

**Если выводит "НЕ НАСТРОЕН" - вернись к шагам 1-2 и перезапусти worker.**

---

## Шаг 5: Тест API напрямую через curl (быстрая проверка)

```bash
curl -X POST "https://d81vybws970pyx-8001.proxy.runpod.net/api/download-video/" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  --output /tmp/test_video.mp4 \
  --max-time 60 \
  --write-out "\nHTTP: %{http_code}, Size: %{size_download} bytes\n"
```

**Проверь файл:**
```bash
ls -lh /tmp/test_video.mp4
```

**Если файл есть и размер > 0 - API работает!**

---

## Шаг 6: Тест через Python в Docker

```bash
docker-compose -f docker-compose.production.yml exec worker python3 -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from app.utils.video.youtube import download_youtube_video
from app.core.config import settings

async def test():
    print('=' * 60)
    print('Тест загрузки YouTube видео через API')
    print('=' * 60)
    print(f'API URL: {settings.YOUTUBE_DOWNLOAD_API_URL or \"НЕ НАСТРОЕН (будет yt-dlp)\"}')
    print()
    
    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    output_path = '/app/data/test_output/test_api.mp4'
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    print(f'Загружаю: {url}')
    print(f'Сохраняю в: {output_path}')
    print()
    
    success = await download_youtube_video(url=url, output_path=output_path, max_retries=2)
    
    print()
    if success and Path(output_path).exists():
        size = Path(output_path).stat().st_size
        print('=' * 60)
        print('✓✓✓ УСПЕХ!')
        print('=' * 60)
        print(f'Файл: {output_path}')
        print(f'Размер: {size / 1024 / 1024:.2f} MB')
    else:
        print('=' * 60)
        print('✗ ОШИБКА')
        print('=' * 60)
        print('Загрузка не удалась')

asyncio.run(test())
"
```

**Должно вывести:**
```
============================================================
✓✓✓ УСПЕХ!
============================================================
Файл: /app/data/test_output/test_api.mp4
Размер: XX.XX MB
```

---

## Шаг 7: Проверка логов

```bash
docker-compose -f docker-compose.production.yml logs worker | grep -i "youtube\|api\|download" | tail -20
```

**Должны быть строки типа:**
```
Downloading via external API: https://...
Download successful via API: ...
```

---

## Шаг 8: Тест через бота (опционально)

1. Отправь боту ссылку на YouTube видео
2. Проверь логи:
```bash
docker-compose -f docker-compose.production.yml logs -f worker | grep -i "api\|download"
```

**Должна быть строка:**
```
Downloading via external API: ...
```

---

## Если что-то не работает:

### Проблема: "API URL: НЕ НАСТРОЕН"
**Решение:**
1. Проверь .env файл
2. Добавь переменную в docker-compose.production.yml
3. Перезапусти worker

### Проблема: "Failed to download video"
**Решение:**
1. Проверь, что API доступен: `curl https://d81vybws970pyx-8001.proxy.runpod.net/api/download-video/`
2. Проверь логи: `docker-compose -f docker-compose.production.yml logs worker | tail -50`

### Проблема: "Connection timeout"
**Решение:**
1. Проверь интернет в контейнере: `docker-compose -f docker-compose.production.yml exec worker ping -c 3 8.8.8.8`
2. Увеличь timeout в коде (если нужно)

---

## Готово!

Если все шаги прошли успешно - API работает! 🎉
