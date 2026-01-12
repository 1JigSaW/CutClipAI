#!/bin/bash

echo "=== Chrome Profile Setup for Docker ==="
echo ""
echo "This script helps you create a Chrome profile with YouTube authentication"
echo "inside the Docker container."
echo ""

read -p "Have you already logged into YouTube on this server with Chrome? (y/n): " answer

if [ "$answer" = "y" ]; then
    echo ""
    echo "Great! Now we'll copy the Chrome profile to the Docker mount point."
    echo ""
    
    if [ -d ~/.config/google-chrome ]; then
        mkdir -p ./data/chrome_profile
        cp -r ~/.config/google-chrome/* ./data/chrome_profile/
        echo "✓ Chrome profile copied to ./data/chrome_profile/"
        
        mkdir -p ./data/keyring
        if [ -d ~/.local/share/keyrings ]; then
            cp -r ~/.local/share/keyrings/* ./data/keyring/ 2>/dev/null || true
            echo "✓ Keyring copied (if available)"
        fi
        
        echo ""
        echo "Now restart the worker container:"
        echo "  docker-compose -f docker-compose.production.yml restart worker"
        echo ""
        echo "Then test:"
        echo "  docker-compose -f docker-compose.production.yml exec worker python3 test_youtube_age_restricted.py 'https://www.youtube.com/watch?v=AGE_RESTRICTED_VIDEO'"
    else
        echo "✗ Chrome profile not found at ~/.config/google-chrome"
        echo "Please login to YouTube first (see instructions below)"
        answer="n"
    fi
fi

if [ "$answer" = "n" ]; then
    echo ""
    echo "You need to setup Chrome on the server first:"
    echo ""
    echo "1. Install Chrome (if not installed):"
    echo "   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    echo "   sudo apt-get install -y ./google-chrome-stable_current_amd64.deb"
    echo ""
    echo "2. Install VNC tools:"
    echo "   sudo apt-get install -y xvfb x11vnc"
    echo ""
    echo "3. Start virtual display:"
    echo "   export DISPLAY=:99"
    echo "   Xvfb :99 -screen 0 1920x1080x24 &"
    echo ""
    echo "4. Start VNC server:"
    echo "   x11vnc -display :99 -nopw -listen localhost -xkb -forever -bg"
    echo ""
    echo "5. Create SSH tunnel from your Mac:"
    echo "   ssh -L 5900:localhost:5900 root@your-server-ip"
    echo ""
    echo "6. Connect VNC Viewer to localhost:5900"
    echo ""
    echo "7. In SSH terminal, start Chrome:"
    echo "   DISPLAY=:99 google-chrome --no-sandbox &"
    echo ""
    echo "8. In VNC window:"
    echo "   - Navigate to youtube.com"
    echo "   - Login to your account"
    echo "   - Open an age-restricted video to verify"
    echo "   - Close Chrome"
    echo ""
    echo "9. Run this script again and answer 'y'"
fi

