# CutClipAI

AI-powered video clipping service with automatic subtitle generation.

## Features

- Automatic video trimming to 30 minutes max
- Whisper-based transcription and subtitle generation
- Intelligent moment selection (20-60 second clips)
- 9:16 aspect ratio cropping for vertical videos
- Coin-based billing system
- Telegram bot interface
- FastAPI backend with Celery workers

## Project Structure

```
app/
  core/           # System configuration
  routers/        # API endpoints
  services/       # Business logic
  workers/        # Background tasks
  utils/          # Helper functions
  bot/            # Telegram bot
```

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

# Start Redis (required)
docker-compose up redis -d

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

## Requirements

- Python 3.10+
- Redis
- ffmpeg
- Whisper (model: medium)
