#!/bin/bash

echo "Starting VNC server for Chrome setup..."
echo ""

export DISPLAY=:99

if ! pgrep -f "Xvfb :99" > /dev/null; then
    echo "Starting Xvfb..."
    Xvfb :99 -screen 0 1920x1080x24 &
    sleep 3
else
    echo "Xvfb already running"
fi

if ! pgrep -f "fluxbox.*:99" > /dev/null; then
    echo "Starting fluxbox..."
    fluxbox -display :99 &
    sleep 2
else
    echo "Fluxbox already running"
fi

if ! pgrep -f "x11vnc.*:99" > /dev/null; then
    echo "Starting x11vnc..."
    x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -shared -bg
    sleep 2
else
    echo "x11vnc already running"
fi

export $(dbus-launch 2>/dev/null) || true
echo -n "" | gnome-keyring-daemon --unlock --components=secrets 2>/dev/null || true

echo ""
echo "VNC server started!"
echo ""
echo "Processes:"
ps aux | grep -E "(Xvfb|x11vnc|fluxbox)" | grep -v grep || echo "No VNC processes found"
echo ""
echo "Port 5900:"
netstat -tlnp 2>/dev/null | grep 5900 || echo "Port 5900 not listening"
echo ""
echo "On your Mac, create SSH tunnel:"
echo "  ssh -L 5900:localhost:5900 root@45.135.234.33"
echo ""
echo "Then connect VNC Viewer to: localhost:5900"
echo ""
echo "Starting Chrome..."
echo ""

DISPLAY=:99 google-chrome --no-sandbox --disable-dev-shm-usage --password-store=basic --user-data-dir=/root/.config/google-chrome &

echo ""
echo "Chrome started!"
echo ""
echo "Now:"
echo "1. Connect VNC to localhost:5900"
echo "2. In Chrome, go to chrome://settings/people and create new profile"
echo "3. In new profile, go to youtube.com and login with verified account"
echo "4. Open an age-restricted video to verify"
echo "5. Close Chrome"
echo ""
echo "Press Ctrl+C when done"

tail -f /dev/null

