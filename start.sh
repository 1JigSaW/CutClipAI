#!/bin/bash

# CutClipAI - Start script
# Stops all running services and starts them fresh with visible logs

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
./stop.sh 2>/dev/null || true

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run: python3 -m venv venv${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Create logs directory
mkdir -p logs

# Start API server
echo -e "${GREEN}🌐 Starting API server...${NC}"
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid
echo -e "${GREEN}   API server started (PID: $API_PID)${NC}"

# Wait for API to be ready (with reload, it takes a bit longer)
echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"
sleep 3  # Give reloader time to start the main process
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API failed to start after 30 seconds${NC}"
        echo -e "${YELLOW}   Check logs: tail -f logs/api.log${NC}"
    fi
    sleep 1
done

# Start Celery worker
echo -e "${GREEN}⚙️  Starting Celery worker...${NC}"
celery -A app.core.celery_app worker --loglevel=info > logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > logs/celery.pid
echo -e "${GREEN}   Celery worker started (PID: $CELERY_PID)${NC}"

# Start Telegram bot
echo -e "${GREEN}🤖 Starting Telegram bot...${NC}"
python3 -m app.bot.bot > logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > logs/bot.pid
echo -e "${GREEN}   Telegram bot started (PID: $BOT_PID)${NC}"

# Wait a bit for services to start
sleep 1

# Show logs from all services
echo ""
echo -e "${GREEN}✅ All services started!${NC}"
echo -e "${YELLOW}📋 Service PIDs:${NC}"
echo -e "   API:    $API_PID"
echo -e "   Celery: $CELERY_PID"
echo -e "   Bot:    $BOT_PID"
echo ""
echo -e "${GREEN}📝 Showing logs (Ctrl+C to stop)...${NC}"
echo ""

# Use multitail if available, otherwise use tail
if command -v multitail >/dev/null 2>&1; then
    multitail -s 2 \
        -cT ansi logs/api.log \
        -cT ansi logs/celery.log \
        -cT ansi logs/bot.log
else
    # Fallback: use tail with colors
    tail -f logs/api.log logs/celery.log logs/bot.log
fi
