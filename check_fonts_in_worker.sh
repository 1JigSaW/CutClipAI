#!/bin/bash
echo "=== Проверка шрифтов в worker контейнере ==="
echo ""
echo "1. Проверка Liberation шрифтов:"
docker-compose -f docker-compose.production.yml exec worker ls -la /usr/share/fonts/truetype/liberation/ 2>&1 || echo "Директория не найдена"
echo ""
echo "2. Проверка DejaVu шрифтов:"
docker-compose -f docker-compose.production.yml exec worker ls -la /usr/share/fonts/truetype/dejavu/ 2>&1 || echo "Директория не найдена"
echo ""
echo "3. Поиск всех TTF шрифтов:"
docker-compose -f docker-compose.production.yml exec worker find /usr/share/fonts -name "*.ttf" -type f | head -20
echo ""
echo "4. Проверка установленных пакетов шрифтов:"
docker-compose -f docker-compose.production.yml exec worker dpkg -l | grep -i font
