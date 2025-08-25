# 🚀 Quick Deployment Guide

## ⚡ **Fastest Way: Railway (Recommended)**

### **Step 1: One-Click Deploy**
```bash
# Make sure you have Node.js installed
node --version

# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy with one command
./deploy_all.sh
```

### **Step 2: Set Environment Variables**
In Railway dashboard, set these variables:
- `BOT_TOKEN` = Your bot token from @BotFather
- `GEMINI_API_KEY` = Your Gemini API key
- `ADMIN_ID` = Your Telegram user ID
- `BOT_USERNAME` = Your bot username
- `GOOGLE_CREDENTIALS_PATH` = `./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json`

## 🐳 **Alternative: Docker**

```bash
# Build and run with Docker
docker build -t telegram-bot .
docker run -d --name telegram-bot --restart unless-stopped \
  -e BOT_TOKEN="your_token" \
  -e GEMINI_API_KEY="your_key" \
  -e ADMIN_ID="your_id" \
  -e BOT_USERNAME="your_username" \
  telegram-bot
```

## 🖥️ **Traditional Server**

```bash
# Upload files to your server
scp -r . user@your-server:/home/user/telegram-bot/

# SSH into server and run
ssh user@your-server
cd telegram-bot
chmod +x deploy.sh
./deploy.sh
```

## 📋 **Pre-Deployment Checklist**

- [ ] Bot token from @BotFather
- [ ] Gemini API key from Google AI Studio
- [ ] Google Cloud credentials uploaded
- [ ] All files in project directory
- [ ] Internet connection for deployment

## 🎯 **Choose Your Path**

| Platform | Difficulty | Cost | Setup Time |
|----------|------------|------|------------|
| **Railway** | ⭐ Easy | 💰 Free tier | ⏱️ 5 minutes |
| **Docker** | ⭐⭐ Medium | 💰 Free | ⏱️ 10 minutes |
| **Server** | ⭐⭐⭐ Hard | 💰 Varies | ⏱️ 20 minutes |

## 🚨 **Troubleshooting**

### **Common Issues:**
1. **Environment Variables**: Ensure all are set correctly
2. **Credentials**: Check Google Cloud JSON file path
3. **Bot Token**: Verify token is active and correct
4. **Dependencies**: All packages are in requirements.txt

### **Quick Fixes:**
```bash
# Check bot syntax
python3 -m py_compile bot3.py

# Test imports
python3 -c "import aiogram; print('OK')"

# View logs
railway logs  # (Railway)
docker logs telegram-bot  # (Docker)
sudo journalctl -u telegram-bot.service -f  # (Server)
```

## 🎉 **After Deployment**

1. **Test bot commands** in Telegram
2. **Check logs** for any errors
3. **Verify Firestore connection**
4. **Test reminder functionality**

## 📞 **Need Help?**

- **Railway**: Check their [documentation](https://docs.railway.app)
- **Docker**: [Docker docs](https://docs.docker.com)
- **Bot Issues**: Check the logs and error messages

---

**🎯 Ready to deploy? Run: `./deploy_all.sh`**


