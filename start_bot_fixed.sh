#!/bin/bash

# Fixed Bot Startup Script
echo "🚀 Starting Fixed Telegram Bot..."

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

# Check if credentials exist
if [ ! -f "credentials/sturdy-lead-454406-n3-16c47cb3a35a.json" ]; then
    echo "❌ Google Cloud credentials not found!"
    echo "Please make sure credentials/sturdy-lead-454406-n3-16c47cb3a35a.json exists"
    exit 1
fi

# Test bot startup
echo "🧪 Testing bot startup..."
python3 -c "
import asyncio
import sys
from aiogram import Bot

async def test_bot():
    try:
        bot = Bot('7189930971:AAEZ4LUYS5lLTotI4ec2W1YmS1CI3CmVmNY')
        info = await bot.get_me()
        print(f'✅ Bot test successful: {info.first_name} (@{info.username})')
        await bot.session.close()
        return True
    except Exception as e:
        print(f'❌ Bot test failed: {e}')
        return False

success = asyncio.run(test_bot())
sys.exit(0 if success else 1)
"

if [ $? -eq 0 ]; then
    echo "🎉 Bot test passed! Starting bot..."
    echo "📱 Bot will start polling for messages..."
    echo "🛑 Press Ctrl+C to stop the bot"
    echo ""
    
    # Start the bot
    python3 bot3.py
else
    echo "💥 Bot test failed! Please check the configuration."
    exit 1
fi
