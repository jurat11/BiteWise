#!/bin/bash

# Local Bot Startup Script
echo "🚀 Starting Telegram Bot locally..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "📋 Please create .env file with your configuration:"
    echo "   cp env_template.txt .env"
    echo "   nano .env"
    echo ""
    echo "Required variables:"
    echo "   BOT_TOKEN=your_bot_token"
    echo "   GEMINI_API_KEY=your_gemini_key"
    echo "   ADMIN_ID=your_admin_id"
    echo "   BOT_USERNAME=your_bot_username"
    echo "   GOOGLE_CREDENTIALS_PATH=./credentials/your-credentials.json"
    exit 1
fi

# Check if credentials file exists
if [ ! -f "credentials/sturdy-lead-454406-n3-16c47cb3a35a.json" ]; then
    echo "⚠️  Google Cloud credentials not found!"
    echo "📋 Please ensure your credentials file is in the credentials/ folder"
    exit 1
fi

# Test bot syntax
echo "🔍 Testing bot syntax..."
python3 -m py_compile bot3.py
if [ $? -ne 0 ]; then
    echo "❌ Bot syntax check failed!"
    exit 1
fi
echo "✅ Bot syntax check passed!"

# Start the bot
echo "🎯 Starting bot..."
echo "📋 Press Ctrl+C to stop the bot"
echo ""
python3 bot3.py


