# Gemini API Setup Guide

## Шаг 1: Получить API ключ

1. Перейдите на https://makersuite.google.com/app/apikey
2. Войдите в свой Google аккаунт
3. Нажмите "Create API Key" или "Get API Key"
4. Скопируйте API ключ (выглядит как `AIzaSy...`)

## Шаг 2: Установить зависимость

```bash
pip install google-generativeai==0.3.2
```

Или если используете requirements.txt:
```bash
pip install -r requirements.txt
```

## Шаг 3: Добавить в .env файл

Создайте или отредактируйте файл `.env` в корне проекта:

```bash
# Gemini API
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-flash  # Options: gemini-1.5-flash (fast) or gemini-1.5-pro (quality)
USE_LLM_ANALYSIS=true
```

Замените `your_api_key_here` на ваш реальный API ключ.

## Шаг 4: Перезапустить сервисы

```bash
./stop.sh
./start.sh
```

## Проверка работы

После запуска в логах должно появиться:
```
LLM analysis enabled | provider=Gemini | model=gemini-1.5-flash
```

Если видите:
```
LLM analysis disabled
```

Проверьте:
- Правильно ли указан `GEMINI_API_KEY` в `.env`
- Установлен ли `USE_LLM_ANALYSIS=true`
- Перезапущены ли сервисы

## Отключение LLM (экономия)

Если хотите отключить LLM анализ (экономия денег):
```bash
USE_LLM_ANALYSIS=false
```

Без LLM будет использоваться только data-driven алгоритм (как раньше).

## Стоимость

- 5 минут видео: ~$0.003
- 30 минут видео: ~$0.005
- 4 часа видео: ~$0.026

## Troubleshooting

### Ошибка: "GEMINI_API_KEY not set"
- Проверьте, что ключ добавлен в `.env`
- Проверьте, что `.env` файл в корне проекта
- Перезапустите сервисы

### Ошибка: "ModuleNotFoundError: No module named 'google.generativeai'"
- Установите: `pip install google-generativeai==0.3.2`
- Или: `pip install -r requirements.txt`

### LLM не работает
- Проверьте логи: `tail -f logs/celery.log`
- Убедитесь, что `USE_LLM_ANALYSIS=true`
- Проверьте, что API ключ валидный

