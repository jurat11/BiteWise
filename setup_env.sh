#!/bin/bash

# Environment Setup Script
echo "🔧 Setting up environment variables..."

# Create .env file with values from bot3.py
cat > .env << 'EOF'
# Bot Configuration
BOT_TOKEN=8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8
GEMINI_API_KEY=AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY
ADMIN_ID=5080813917
BOT_USERNAME=@KinoMania4k_Bot

# Google Cloud Configuration
GOOGLE_CREDENTIALS_PATH=./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json
EOF

echo "✅ .env file created successfully!"
echo "📋 Environment variables set:"
echo "   BOT_TOKEN: 8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"
echo "   GEMINI_API_KEY: AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY"
echo "   ADMIN_ID: 5080813917"
echo "   BOT_USERNAME: @KinoMania4k_Bot"
echo "   GOOGLE_CREDENTIALS_PATH: ./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json"
echo ""
echo "🚀 Now you can deploy with: ./deploy_all.sh"


