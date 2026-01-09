# 🚀 CutClipAI Deployment Guide

Простая инструкция для развертывания на сервере Contabo.

## 📋 Требования

- Ubuntu 22.04/24.04
- Docker и Docker Compose
- 16+ GB RAM
- 100+ GB SSD

---

## 🔧 Шаг 1: Подготовка сервера

### На сервере (SSH: root@45.88.223.140):

```bash
# Загрузи и запусти скрипт настройки
wget https://raw.githubusercontent.com/YOUR_REPO/main/setup-server.sh
bash setup-server.sh
```

Или вручную:

```bash
# Обнови систему
apt update && apt upgrade -y

# Установи Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установи Docker Compose
apt install -y docker-compose git

# Создай директорию
mkdir -p /opt/cutclipai
cd /opt/cutclipai
```

---

## 📦 Шаг 2: Загрузка проекта

### Вариант A: Через Git (рекомендуется)

```bash
cd /opt/cutclipai
git clone https://github.com/YOUR_USERNAME/CutClipAI.git .
```

### Вариант B: Через SCP (с локальной машины)

```bash
# На твоем Mac
cd /Users/jigsaw/Projects/CutClipAI
scp -r . root@45.88.223.140:/opt/cutclipai/
```

---

## ⚙️ Шаг 3: Настройка окружения

```bash
cd /opt/cutclipai

# Создай .env из примера
cp env.example.production .env

# Отредактируй .env
nano .env
```

### Обязательно заполни:

```bash
# API ключи
TELEGRAM_BOT_TOKEN=your_token_here
ASSEMBLY_AI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# S3/B2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=cutclipai

# URL сервера
API_BASE_URL=http://45.88.223.140:8000
```

Сохрани: `Ctrl+O`, Enter, `Ctrl+X`

---

## 🚀 Шаг 4: Запуск

```bash
cd /opt/cutclipai

# Запусти deployment
bash deploy.sh
```

Скрипт автоматически:
- ✅ Создаст директории
- ✅ Соберет Docker образы
- ✅ Запустит миграции БД
- ✅ Запустит все сервисы

---

## 📊 Проверка статуса

```bash
# Проверь здоровье сервисов
bash health-check.sh

# Или вручную:
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f
```

---

## 🔄 Управление

### Просмотр логов:
```bash
# Все сервисы
docker-compose -f docker-compose.production.yml logs -f

# Только бот
docker-compose -f docker-compose.production.yml logs -f bot

# Только worker
docker-compose -f docker-compose.production.yml logs -f worker
```

### Перезапуск:
```bash
docker-compose -f docker-compose.production.yml restart

# Или конкретный сервис
docker-compose -f docker-compose.production.yml restart worker
```

### Остановка:
```bash
docker-compose -f docker-compose.production.yml down
```

### Обновление кода:
```bash
cd /opt/cutclipai
git pull
bash deploy.sh
```

### Очистка диска:
```bash
bash cleanup.sh
```

---

## 🌐 Доступ к сервисам

- **API**: http://45.88.223.140:8000
- **API Docs**: http://45.88.223.140:8000/docs
- **Telegram Bot**: отправь `/start` своему боту

---

## 🐛 Troubleshooting

### Не запускается worker:
```bash
# Проверь память
free -h

# Увеличь swap если мало RAM
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

### Заполнен диск:
```bash
# Очисти temp файлы
bash cleanup.sh

# Проверь место
df -h
du -sh /opt/cutclipai/data/*
```

### Не работает бот:
```bash
# Проверь логи
docker-compose -f docker-compose.production.yml logs bot

# Проверь токен
docker-compose -f docker-compose.production.yml exec bot env | grep TELEGRAM
```

### Медленная обработка:
```bash
# Проверь ресурсы
docker stats

# Увеличь concurrency в docker-compose.production.yml
# worker -> command -> --concurrency=3
```

---

## 📈 Мониторинг

### Установи cron для автоочистки:
```bash
crontab -e
```

Добавь:
```
# Очистка temp файлов каждый день в 2:00
0 2 * * * cd /opt/cutclipai && bash cleanup.sh >> /var/log/cutclipai-cleanup.log 2>&1

# Health check каждые 5 минут
*/5 * * * * cd /opt/cutclipai && bash health-check.sh >> /var/log/cutclipai-health.log 2>&1
```

---

## 🔒 Безопасность

### Firewall:
```bash
ufw allow 22/tcp
ufw allow 8000/tcp
ufw enable
```

### Смени пароль БД:
В `.env`:
```bash
POSTGRES_PASSWORD=your_very_secure_password_here
```

Затем:
```bash
bash deploy.sh
```

---

## 💰 Оптимизация затрат

- Временные файлы автоматически удаляются после обработки
- Используй `cleanup.sh` для ручной очистки
- AssemblyAI кеширует результаты транскрипции
- S3 для долговременного хранения (дешевле локального диска)

---

## 📞 Помощь

Если что-то не работает:
1. Проверь логи: `docker-compose -f docker-compose.production.yml logs`
2. Проверь статус: `bash health-check.sh`
3. Проверь .env файл
4. Перезапусти: `bash deploy.sh`

