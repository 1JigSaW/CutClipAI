#!/bin/bash

# CutClipAI - Stop script
# Stops all running services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping CutClipAI services...${NC}"

# Stop processes by PID files
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid 2>/dev/null || echo "")
    if [ ! -z "$API_PID" ] && ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}   Stopping API server (PID: $API_PID)...${NC}"
        kill $API_PID 2>/dev/null || true
        rm -f logs/api.pid
    fi
fi

if [ -f "logs/celery.pid" ]; then
    CELERY_PID=$(cat logs/celery.pid 2>/dev/null || echo "")
    if [ ! -z "$CELERY_PID" ] && ps -p $CELERY_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}   Stopping Celery worker (PID: $CELERY_PID)...${NC}"
        kill $CELERY_PID 2>/dev/null || true
        rm -f logs/celery.pid
    fi
fi

if [ -f "logs/bot.pid" ]; then
    BOT_PID=$(cat logs/bot.pid 2>/dev/null || echo "")
    if [ ! -z "$BOT_PID" ] && ps -p $BOT_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}   Stopping Telegram bot (PID: $BOT_PID)...${NC}"
        kill $BOT_PID 2>/dev/null || true
        rm -f logs/bot.pid
    fi
fi

# Kill processes by name (fallback)
echo -e "${YELLOW}   Checking for remaining processes...${NC}"

# Kill uvicorn processes
pkill -f "uvicorn app.api.main:app" 2>/dev/null || true

# Kill celery processes
pkill -f "celery -A app.core.celery_app worker" 2>/dev/null || true

# Kill bot processes
pkill -f "python3 -m app.bot.bot" 2>/dev/null || true

# Wait a bit for processes to stop
sleep 1

# Force kill if still running
pkill -9 -f "uvicorn app.api.main:app" 2>/dev/null || true
pkill -9 -f "celery -A app.core.celery_app worker" 2>/dev/null || true
pkill -9 -f "python3 -m app.bot.bot" 2>/dev/null || true

echo -e "${GREEN}✅ All services stopped${NC}"

