#!/bin/bash

set -e

echo "🚀 CutClipAI Deployment Script"
echo "================================"

if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from env.example.production..."
    cp env.example.production .env
    echo "✅ .env created. Please edit it with your credentials:"
    echo "   nano .env"
    echo ""
    echo "Press Enter after you've configured .env..."
    read
fi

echo "📦 Creating directories..."
mkdir -p data/temp data/output logs

echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.production.yml down

echo "🗑️  Cleaning up old temp files..."
find data/temp -type f -mtime +1 -delete 2>/dev/null || true

echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🔄 Running database migrations..."
docker-compose -f docker-compose.production.yml run --rm api alembic upgrade head || echo "⚠️  Migration failed or not needed"

echo "🚀 Starting services..."
docker-compose -f docker-compose.production.yml up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "📊 Checking service status..."
docker-compose -f docker-compose.production.yml ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Useful commands:"
echo "  View logs:       docker-compose -f docker-compose.production.yml logs -f"
echo "  Check status:    docker-compose -f docker-compose.production.yml ps"
echo "  Restart:         docker-compose -f docker-compose.production.yml restart"
echo "  Stop:            docker-compose -f docker-compose.production.yml down"
echo ""
echo "🌐 Your API should be available at: http://$(hostname -I | awk '{print $1}'):8000"
echo "📚 API docs: http://$(hostname -I | awk '{print $1}'):8000/docs"

