#!/bin/bash

# Bot Deployment Script
# This script helps deploy your Telegram bot to a server

echo "🚀 Starting bot deployment..."

# Check if running on server (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "✅ Running on Linux server"
    
    # Update system packages
    echo "📦 Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    
    # Install Python and pip if not present
    if ! command -v python3 &> /dev/null; then
        echo "🐍 Installing Python 3..."
        sudo apt install python3 python3-pip python3-venv -y
    fi
    
    # Install system dependencies
    echo "🔧 Installing system dependencies..."
    sudo apt install -y build-essential python3-dev
    
    # Create virtual environment
    echo "🏗️ Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    echo "📚 Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create systemd service file
    echo "⚙️ Creating systemd service..."
    sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python3 bot3.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    echo "🔄 Reloading systemd and enabling service..."
    sudo systemctl daemon-reload
    sudo systemctl enable telegram-bot.service
    sudo systemctl start telegram-bot.service
    
    echo "✅ Bot deployed successfully!"
    echo "📋 Service status: sudo systemctl status telegram-bot.service"
    echo "📋 View logs: sudo journalctl -u telegram-bot.service -f"
    echo "📋 Stop bot: sudo systemctl stop telegram-bot.service"
    echo "📋 Start bot: sudo systemctl start telegram-bot.service"
    
else
    echo "⚠️ Not running on Linux server"
    echo "📋 This script is designed for Linux server deployment"
    echo "📋 For local development, run: python3 bot3.py"
fi


