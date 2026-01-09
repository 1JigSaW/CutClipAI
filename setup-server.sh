#!/bin/bash

set -e

echo "🔧 Server Setup Script for CutClipAI"
echo "====================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root (use: sudo bash setup-server.sh)"
    exit 1
fi

echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

echo "📦 Installing required packages..."
apt-get install -y \
    curl \
    git \
    wget \
    vim \
    nano \
    htop \
    screen \
    ca-certificates \
    gnupg \
    lsb-release

echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

echo "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

echo "🔒 Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 8000/tcp
    ufw --force enable
    echo "✅ Firewall configured"
else
    echo "⚠️  UFW not found, skipping firewall setup"
fi

echo "⚙️  Configuring Docker..."
systemctl enable docker
systemctl start docker

echo "👤 Creating project directory..."
mkdir -p /opt/cutclipai
cd /opt/cutclipai

echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/cutclipai << EOF
/opt/cutclipai/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF

echo "⏰ Setting up cron job for cleanup..."
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/cutclipai && bash cleanup.sh >> /var/log/cutclipai-cleanup.log 2>&1") | crontab -

echo ""
echo "✅ Server setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Clone your project to /opt/cutclipai"
echo "   cd /opt/cutclipai"
echo "   git clone YOUR_REPO_URL ."
echo ""
echo "2. Configure environment:"
echo "   cp .env.production.example .env"
echo "   nano .env"
echo ""
echo "3. Deploy:"
echo "   bash deploy.sh"
echo ""
echo "🎉 Ready to deploy CutClipAI!"

