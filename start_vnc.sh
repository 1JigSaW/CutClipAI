#!/bin/bash

echo "Starting VNC server for Chrome setup..."
echo ""
echo "This will:"
echo "1. Start virtual display"
echo "2. Start VNC server on port 5900"
echo "3. Launch Chrome browser"
echo ""

export DISPLAY=:99

Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

fluxbox -display :99 &
sleep 2

x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -shared -bg

sleep 2

export $(dbus-launch)
echo -n "" | gnome-keyring-daemon --unlock --components=secrets

echo ""
echo "VNC server started!"
echo ""
echo "On your Mac, create SSH tunnel:"
echo "  ssh -L 5900:localhost:5900 root@your-server-ip"
echo ""
echo "Then connect VNC Viewer to: localhost:5900"
echo ""
echo "Starting Chrome..."
echo ""

DISPLAY=:99 google-chrome --no-sandbox --disable-dev-shm-usage --user-data-dir=/root/.config/google-chrome &

echo ""
echo "Chrome started!"
echo ""
echo "Now:"
echo "1. Connect VNC to localhost:5900"
echo "2. In Chrome, go to youtube.com and login"
echo "3. Open an age-restricted video to verify"
echo "4. Close Chrome"
echo "5. Exit this container"
echo "6. Restart worker: docker-compose -f docker-compose.production.yml restart worker"
echo ""
echo "Press Ctrl+C when done"

tail -f /dev/null

