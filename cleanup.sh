#!/bin/bash

echo "🧹 CutClipAI Cleanup Script"
echo "==========================="
echo ""

echo "🗑️  Cleaning temp files older than 1 day..."
find data/temp -type f -mtime +1 -delete 2>/dev/null || true
echo "✅ Temp files cleaned"

echo ""
echo "🗑️  Cleaning Docker unused images..."
docker image prune -f
echo "✅ Docker images cleaned"

echo ""
echo "🗑️  Cleaning Docker build cache..."
docker builder prune -f
echo "✅ Docker cache cleaned"

echo ""
echo "📊 Disk usage after cleanup:"
df -h / | grep -v Filesystem
echo ""
du -sh data/temp data/output logs 2>/dev/null || echo "No data directories"

echo ""
echo "✅ Cleanup complete!"

