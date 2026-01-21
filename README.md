# CutClipAI

AI-powered video clipping service with automatic subtitle generation.

## Features

- Whisper-based transcription and subtitle generation
- Intelligent moment selection (20-60 second clips)
- 9:16 aspect ratio cropping for vertical videos
- Coin-based billing system
- Telegram bot interface
- FastAPI backend with Celery workers
- YouTube video support (direct link paste)
- Google Drive integration

## Project Structure

```
app/
  api/            # FastAPI application entry point
  bot/            # Telegram bot (handlers, keyboards, messages)
  core/           # System configuration (config, database, logger, celery)
  models/         # Database models (SQLAlchemy)
  routers/        # API endpoints (FastAPI routes)
  services/       # Business logic (video processing, billing, storage)
  workers/        # Background tasks (Celery workers)
  utils/          # Helper functions (video utils, validators)
```

**Подробная документация:** См. [ARCHITECTURE.md](./ARCHITECTURE.md)

### Основные компоненты

- **routers/** - HTTP endpoints, валидация запросов
- **services/** - Вся бизнес-логика (обработка видео, биллинг)
- **workers/** - Фоновые задачи через Celery
- **bot/** - Telegram бот (обработчики, клавиатуры)
- **utils/** - Переиспользуемые утилиты
- **core/** - Системная конфигурация

## Quickstart

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env and add your TELEGRAM_BOT_TOKEN
```

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (required)
docker-compose up postgres redis -d

# Run database migrations
alembic upgrade head

# Start API
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# Start Celery worker (in another terminal)
celery -A app.core.celery_app worker --loglevel=info

# Start Telegram bot (in another terminal)
python3 -m app.bot.bot
```

### 3. Docker Compose

```bash
docker-compose up
```

## Usage

The bot accepts:
- Video files (up to 4GB via Telegram)
- YouTube links (paste any YouTube URL)
- Google Drive links (with public access)

## API Endpoints

- `GET /health` - Health check
- `POST /video/process` - Upload and process video
- `GET /video/status/{task_id}` - Check processing status
- `GET /billing/balance/{user_id}` - Get user balance
- `POST /billing/buy` - Buy coins

## Billing

- New users start with 5 coins
- 1 clip = 1 coin
- Buy coins: 5 / 20 / 50 coins

## Database

The project uses PostgreSQL for persistent storage. Database migrations are managed with Alembic.

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description"

# Rollback last migration
alembic downgrade -1
```

### Database Models

- **User** - User accounts with Telegram ID and balance
- **Transaction** - Transaction history (purchases, charges, refunds)
- **VideoTask** - Video processing tasks with status tracking

## Requirements

- Python 3.10+
- PostgreSQL 16+
- Redis
- ffmpeg
- Whisper (model: medium)
