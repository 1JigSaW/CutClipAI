#!/bin/bash

echo "🏥 CutClipAI Health Check"
echo "========================="
echo ""

check_service() {
    local service=$1
    local status=$(docker-compose -f docker-compose.production.yml ps -q $service 2>/dev/null)
    
    if [ -z "$status" ]; then
        echo "❌ $service: Not running"
        return 1
    else
        local health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose -f docker-compose.production.yml ps -q $service) 2>/dev/null || echo "unknown")
        if [ "$health" = "healthy" ] || [ "$health" = "unknown" ]; then
            echo "✅ $service: Running"
            return 0
        else
            echo "⚠️  $service: Running but unhealthy ($health)"
            return 1
        fi
    fi
}

check_service "postgres"
check_service "redis"
check_service "api"
check_service "worker"
check_service "bot"

echo ""
echo "📊 Resource Usage:"
echo "==================="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose -f docker-compose.production.yml ps -q)

echo ""
echo "💾 Disk Usage:"
echo "==============="
du -sh data/temp data/output 2>/dev/null || echo "No data directories"

echo ""
echo "📝 Recent logs (last 20 lines):"
echo "================================="
docker-compose -f docker-compose.production.yml logs --tail=20

