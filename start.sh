#!/bin/bash

# CutClipAI - Start script
# Stops all running services and starts them fresh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting CutClipAI services...${NC}"

# Stop existing processes
echo -e "${YELLOW}📛 Stopping existing processes...${NC}"
./stop.sh

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run: python3 -m venv venv${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Start PostgreSQL and Redis (via Docker Compose)
echo -e "${GREEN}🐘 Starting PostgreSQL and Redis...${NC}"
docker-compose up postgres redis -d

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 5
until docker-compose exec -T postgres pg_isready -U cutclipai > /dev/null 2>&1; do
    echo -e "${YELLOW}   Waiting for PostgreSQL...${NC}"
    sleep 2
done
echo -e "${GREEN}✅ PostgreSQL is ready${NC}"

# Run database migrations
echo -e "${GREEN}📊 Running database migrations...${NC}"
alembic upgrade head

# Create logs directory
mkdir -p logs

# Start API server
echo -e "${GREEN}🌐 Starting API server...${NC}"
nohup uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid
echo -e "${GREEN}   API server started (PID: $API_PID)${NC}"

# Wait for API to be ready
echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"
sleep 3
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Start Celery worker
echo -e "${GREEN}⚙️  Starting Celery worker...${NC}"
nohup celery -A app.core.celery_app worker --loglevel=info > logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > logs/celery.pid
echo -e "${GREEN}   Celery worker started (PID: $CELERY_PID)${NC}"

# Start Telegram bot
echo -e "${GREEN}🤖 Starting Telegram bot...${NC}"
nohup python3 -m app.bot.bot > logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > logs/bot.pid
echo -e "${GREEN}   Telegram bot started (PID: $BOT_PID)${NC}"

# Summary
echo ""
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo -e "${GREEN}📋 Service status:${NC}"
echo -e "   API:      http://localhost:8000 (PID: $API_PID)"
echo -e "   Celery:   Running (PID: $CELERY_PID)"
echo -e "   Bot:      Running (PID: $BOT_PID)"
echo ""
echo -e "${YELLOW}📝 Logs:${NC}"
echo -e "   API:      tail -f logs/api.log"
echo -e "   Celery:   tail -f logs/celery.log"
echo -e "   Bot:      tail -f logs/bot.log"
echo ""
echo -e "${YELLOW}🛑 To stop all services: ./stop.sh${NC}"

