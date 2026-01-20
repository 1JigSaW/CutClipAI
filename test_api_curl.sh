#!/bin/bash
set -e

API_URL="${YOUTUBE_DOWNLOAD_API_URL:-https://d81vybws970pyx-8001.proxy.runpod.net}"
TEST_URL="${1:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"

echo "=== Тест YouTube API ==="
echo ""
echo "API URL: $API_URL"
echo "Video URL: $TEST_URL"
echo ""

echo "1. Тест POST запроса..."
curl -X POST "$API_URL/api/download-video/" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$TEST_URL\"}" \
  --output /tmp/test_post.mp4 \
  --write-out "\nHTTP Status: %{http_code}\nSize: %{size_download} bytes\n" \
  --max-time 60

if [ -f /tmp/test_post.mp4 ] && [ -s /tmp/test_post.mp4 ]; then
    echo "✓ POST запрос успешен"
    ls -lh /tmp/test_post.mp4
    rm /tmp/test_post.mp4
else
    echo "✗ POST запрос не удался"
fi

echo ""
echo "2. Тест GET запроса..."
curl "$API_URL/api/download-video/?url=$TEST_URL" \
  --output /tmp/test_get.mp4 \
  --write-out "\nHTTP Status: %{http_code}\nSize: %{size_download} bytes\n" \
  --max-time 60

if [ -f /tmp/test_get.mp4 ] && [ -s /tmp/test_get.mp4 ]; then
    echo "✓ GET запрос успешен"
    ls -lh /tmp/test_get.mp4
    rm /tmp/test_get.mp4
else
    echo "✗ GET запрос не удался"
fi

echo ""
echo "=== Готово! ==="
