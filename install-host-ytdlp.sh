#!/bin/bash

echo "Installing yt-dlp on HOST..."

apt-get update
apt-get install -y python3-pip ffmpeg

pip3 install --upgrade yt-dlp

yt-dlp --version

echo "yt-dlp installed successfully!"
echo "Now setting up SSH access from Docker container..."

echo ""
echo "Run these commands ON THE SERVER after starting the bot:"
echo ""
echo "  # Get the public key from the bot container"
echo "  docker-compose -f docker-compose.production.yml exec bot cat /root/.ssh/id_rsa.pub"
echo ""
echo "  # Add it to host authorized_keys"
echo "  docker-compose -f docker-compose.production.yml exec bot cat /root/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys"
echo "  chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "  # Test SSH connection from container to host"
echo "  docker-compose -f docker-compose.production.yml exec bot ssh -o StrictHostKeyChecking=no root@172.17.0.1 'echo SSH works!'"
echo ""

