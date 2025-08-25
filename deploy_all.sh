#!/bin/bash

# Multi-Platform Bot Deployment Script
echo "🚀 Multi-Platform Bot Deployment Script"
echo "======================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to deploy to Railway
deploy_railway() {
    echo "🚂 Deploying to Railway..."
    
    if ! command_exists railway; then
        echo "📦 Installing Railway CLI..."
        npm install -g @railway/cli
    fi
    
    if ! railway whoami >/dev/null 2>&1; then
        echo "🔐 Please login to Railway first:"
        railway login
        return 1
    fi
    
    echo "⚙️ Setting up Railway project..."
    railway init --yes
    
    echo "🔧 Setting environment variables..."
    railway variables set BOT_TOKEN="$BOT_TOKEN"
    railway variables set GEMINI_API_KEY="$GEMINI_API_KEY"
    railway variables set ADMIN_ID="$ADMIN_ID"
    railway variables set BOT_USERNAME="$BOT_USERNAME"
    railway variables set GOOGLE_CREDENTIALS_PATH="./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json"
    
    echo "🚀 Deploying to Railway..."
    railway up
    
    echo "✅ Railway deployment complete!"
    echo "📋 View logs: railway logs"
    echo "🌐 Get domain: railway domain"
}

# Function to deploy to Docker
deploy_docker() {
    echo "🐳 Deploying with Docker..."
    
    if ! command_exists docker; then
        echo "❌ Docker not found. Please install Docker first."
        return 1
    fi
    
    echo "🏗️ Building Docker image..."
    docker build -t telegram-bot .
    
    echo "🚀 Running Docker container..."
    docker run -d \
        --name telegram-bot \
        --restart unless-stopped \
        -e BOT_TOKEN="$BOT_TOKEN" \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e ADMIN_ID="$ADMIN_ID" \
        -e BOT_USERNAME="$BOT_USERNAME" \
        -e GOOGLE_CREDENTIALS_PATH="./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json" \
        telegram-bot
    
    echo "✅ Docker deployment complete!"
    echo "📋 View logs: docker logs telegram-bot"
    echo "🔄 Restart: docker restart telegram-bot"
}

# Function to deploy to traditional server
deploy_server() {
    echo "🖥️ Deploying to traditional server..."
    
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        echo "⚠️ This deployment method is designed for Linux servers"
        echo "📋 For local deployment, use: ./start_bot.sh"
        return 1
    fi
    
    echo "📦 Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    
    echo "🐍 Installing Python and dependencies..."
    sudo apt install -y python3 python3-pip python3-venv build-essential python3-dev
    
    echo "🏗️ Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "📚 Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
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
Environment=BOT_TOKEN=$BOT_TOKEN
Environment=GEMINI_API_KEY=$GEMINI_API_KEY
Environment=ADMIN_ID=$ADMIN_ID
Environment=BOT_USERNAME=$BOT_USERNAME
Environment=GOOGLE_CREDENTIALS_PATH=$(pwd)/credentials/sturdy-lead-454406-n3-16c47cb3a35a.json
ExecStart=$(pwd)/venv/bin/python3 bot3.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo "🔄 Enabling and starting service..."
    sudo systemctl daemon-reload
    sudo systemctl enable telegram-bot.service
    sudo systemctl start telegram-bot.service
    
    echo "✅ Server deployment complete!"
    echo "📋 Service status: sudo systemctl status telegram-bot.service"
    echo "📋 View logs: sudo journalctl -u telegram-bot.service -f"
}

# Main deployment logic
main() {
    echo "🎯 Choose deployment method:"
    echo "1) Railway (Recommended - Free, Easy)"
    echo "2) Docker (Containerized)"
    echo "3) Traditional Server (Linux)"
    echo "4) Local Development"
    echo ""
    
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            deploy_railway
            ;;
        2)
            deploy_docker
            ;;
        3)
            deploy_server
            ;;
        4)
            echo "🚀 Starting local development..."
            ./start_bot.sh
            ;;
        *)
            echo "❌ Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
}

# Check if environment variables are set
if [ -z "$BOT_TOKEN" ] || [ -z "$GEMINI_API_KEY" ] || [ -z "$ADMIN_ID" ] || [ -z "$BOT_USERNAME" ]; then
    echo "⚠️ Environment variables not set!"
    echo "📋 Please set these variables first:"
    echo "   export BOT_TOKEN='your_bot_token'"
    echo "   export GEMINI_API_KEY='your_gemini_key'"
    echo "   export ADMIN_ID='your_admin_id'"
    echo "   export BOT_USERNAME='your_bot_username'"
    echo ""
    echo "Or create a .env file and source it:"
    echo "   cp env_template.txt .env"
    echo "   nano .env  # Edit with your values"
    echo "   source .env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Run main function
main


