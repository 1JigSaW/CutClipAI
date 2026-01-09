# ⚡ Quick Start - Развертывание за 5 минут

## 🎯 Для Contabo Cloud VPS 30 (45.88.223.140)

### 📝 Шаг 1: Подключись к серверу

```bash
ssh root@45.88.223.140
```

---

### 🔧 Шаг 2: Установи Docker (один раз)

```bash
# Скопируй и вставь всё сразу:
apt update && apt upgrade -y && \
curl -fsSL https://get.docker.com -o get-docker.sh && \
sh get-docker.sh && \
apt install -y docker-compose git && \
rm get-docker.sh
```

---

### 📦 Шаг 3: Загрузи проект

#### Вариант A: Через Git (если репо на GitHub)

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/CutClipAI.git cutclipai
cd /opt/cutclipai
```

#### Вариант B: Загрузить с локальной машины

**На твоём Mac:**
```bash
cd /Users/jigsaw/Projects/CutClipAI
scp -r . root@45.88.223.140:/opt/cutclipai/
```

**Потом на сервере:**
```bash
cd /opt/cutclipai
```

---

### ⚙️ Шаг 4: Настрой .env

```bash
# Создай .env из примера
cp env.example.production .env

# Отредактируй
nano .env
```

**Замени эти строки:**

```bash
API_BASE_URL=http://45.88.223.140:8000

TELEGRAM_BOT_TOKEN=123456:ABC-DEF...  # твой токен от @BotFather
ASSEMBLY_AI_API_KEY=abc123...         # ключ от AssemblyAI
OPENAI_API_KEY=sk-proj-...            # ключ от OpenAI

# S3 credentials
AWS_ACCESS_KEY_ID=твой_ключ
AWS_SECRET_ACCESS_KEY=твой_секрет
S3_BUCKET_NAME=cutclipai
```

Сохрани: `Ctrl+O`, Enter, `Ctrl+X`

---

### 🚀 Шаг 5: ЗАПУСТИ!

```bash
# Сделай скрипты исполняемыми
chmod +x *.sh

# Запусти deployment
bash deploy.sh
```

Всё! Скрипт автоматически:
- ✅ Создаст директории
- ✅ Соберёт Docker образы
- ✅ Запустит БД миграции  
- ✅ Запустит все сервисы

---

### ✅ Шаг 6: Проверь

```bash
# Проверь статус
bash health-check.sh

# Или посмотри логи
docker-compose -f docker-compose.production.yml logs -f
```

Открой в браузере:
- API: http://45.88.223.140:8000/docs
- Отправь `/start` своему Telegram боту

---

## 🔄 Частые команды

```bash
# Перезапустить
docker-compose -f docker-compose.production.yml restart

# Остановить
docker-compose -f docker-compose.production.yml down

# Посмотреть логи
docker-compose -f docker-compose.production.yml logs -f worker

# Очистить диск
bash cleanup.sh

# Health check
bash health-check.sh

# Обновить код (если через git)
git pull && bash deploy.sh
```

---

## 🐛 Если что-то не работает

### Проблема: Нет места на диске
```bash
bash cleanup.sh
docker system prune -af
```

### Проблема: Бот не отвечает
```bash
# Проверь логи
docker-compose -f docker-compose.production.yml logs bot

# Проверь токен
docker-compose -f docker-compose.production.yml exec bot env | grep TELEGRAM
```

### Проблема: Worker падает
```bash
# Добавь swap
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 📊 Мониторинг

```bash
# Ресурсы
docker stats

# Диск
df -h
du -sh /opt/cutclipai/data/*

# Процессы
htop
```

---

## 🎉 Готово!

Теперь твой бот работает на **Contabo VPS 30**!

**IP:** 45.88.223.140  
**API:** http://45.88.223.140:8000  
**Docs:** http://45.88.223.140:8000/docs

Отправь `/start` боту в Telegram и тестируй! 🚀

