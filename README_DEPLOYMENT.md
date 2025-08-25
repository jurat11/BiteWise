# Telegram Bot Deployment Guide

## 🚀 Quick Start

### 1. Fix Bot Issues (Already Done)
- ✅ Removed duplicate decorators
- ✅ Fixed code structure
- ✅ Moved admin functions to proper location
- ✅ Fixed syntax errors

### 2. Local Testing
```bash
# Test if bot runs without errors
python3 -m py_compile bot3.py

# Run the bot locally
python3 bot3.py
```

### 3. Server Deployment

#### Option A: Automated Deployment (Recommended)
```bash
# Upload files to your server
# Make sure to include:
# - bot3.py
# - requirements.txt
# - credentials/ folder with your Google Cloud JSON
# - deploy.sh

# Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

#### Option B: Manual Deployment
```bash
# 1. Connect to your server
ssh user@your-server-ip

# 2. Install Python and dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv build-essential python3-dev

# 3. Create project directory
mkdir ~/telegram-bot
cd ~/telegram-bot

# 4. Upload your files (use scp, git, or file manager)
# - bot3.py
# - requirements.txt
# - credentials/ folder

# 5. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Create systemd service
sudo nano /etc/systemd/system/telegram-bot.service
```

#### Systemd Service File
```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/telegram-bot
Environment=PATH=/home/your-username/telegram-bot/venv/bin
ExecStart=/home/your-username/telegram-bot/venv/bin/python3 bot3.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 8. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
```

### 4. Environment Configuration

Create a `.env` file on your server:
```bash
# Copy the template
cp env_template.txt .env

# Edit with your actual values
nano .env
```

Required values:
- `BOT_TOKEN`: Your Telegram bot token from @BotFather
- `GEMINI_API_KEY`: Your Google Gemini API key
- `ADMIN_ID`: Your Telegram user ID
- `BOT_USERNAME`: Your bot's username
- `GOOGLE_CREDENTIALS_PATH`: Path to your Google Cloud credentials JSON

### 5. Google Cloud Setup

1. **Create a Google Cloud Project**
2. **Enable Firestore API**
3. **Create Service Account**
4. **Download JSON credentials**
5. **Upload to server in `credentials/` folder**

### 6. Monitoring and Management

```bash
# Check service status
sudo systemctl status telegram-bot.service

# View logs
sudo journalctl -u telegram-bot.service -f

# Restart bot
sudo systemctl restart telegram-bot.service

# Stop bot
sudo systemctl stop telegram-bot.service

# Start bot
sudo systemctl start telegram-bot.service
```

### 7. Troubleshooting

#### Common Issues:
1. **Permission Denied**: Check file permissions and ownership
2. **Import Errors**: Ensure all dependencies are installed in virtual environment
3. **Firestore Connection**: Verify Google Cloud credentials and API access
4. **Bot Token**: Ensure bot token is correct and bot is not blocked

#### Debug Commands:
```bash
# Test Python imports
python3 -c "import aiogram; import google.cloud.firestore; print('All imports successful')"

# Check bot file syntax
python3 -m py_compile bot3.py

# Run with verbose output
python3 bot3.py --verbose
```

### 8. Security Considerations

- ✅ Keep credentials secure
- ✅ Use environment variables for sensitive data
- ✅ Regularly update dependencies
- ✅ Monitor bot logs for suspicious activity
- ✅ Use HTTPS for webhook endpoints (if applicable)

### 9. Backup and Updates

```bash
# Backup current version
cp bot3.py bot3.py.backup.$(date +%Y%m%d)

# Update bot
git pull origin main  # if using git
# or manually upload new version

# Restart service
sudo systemctl restart telegram-bot.service
```

## 📞 Support

If you encounter issues:
1. Check the logs: `sudo journalctl -u telegram-bot.service -f`
2. Verify all dependencies are installed
3. Ensure environment variables are set correctly
4. Check Google Cloud API access and quotas

## 🎯 Next Steps

After successful deployment:
1. Test all bot commands
2. Set up monitoring and alerts
3. Configure backup strategies
4. Plan for scaling if needed


