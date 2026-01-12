#!/bin/bash

export $(dbus-launch)

echo "Initializing gnome-keyring..."

mkdir -p ~/.local/share/keyrings

echo -n "" | gnome-keyring-daemon --unlock --components=secrets 2>/dev/null

if [ -f ~/.config/google-chrome/Default/Cookies ]; then
    echo "Chrome profile found"
    ls -lh ~/.config/google-chrome/Default/Cookies
else
    echo "Chrome profile not found at ~/.config/google-chrome/Default/Cookies"
fi

echo "Keyring initialized"

