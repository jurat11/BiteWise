# 🚂 Railway Deployment Guide

## Quick Deploy to Railway

### Step 1: Install Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login
```

### Step 2: Initialize Railway Project
```bash
# Navigate to your project directory
cd /path/to/MyBotProject

# Initialize Railway project
railway init

# Link to existing project (if you have one)
# railway link
```

### Step 3: Set Environment Variables
```bash
# Set your bot token
railway variables set BOT_TOKEN="your_bot_token_here"

# Set Gemini API key
railway variables set GEMINI_API_KEY="your_gemini_api_key_here"

# Set admin ID
railway variables set ADMIN_ID="your_admin_telegram_id"

# Set bot username
railway variables set BOT_USERNAME="your_bot_username"

# Set Google credentials path
railway variables set GOOGLE_CREDENTIALS_PATH="./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json"
```

### Step 4: Deploy
```bash
# Deploy to Railway
railway up

# Check deployment status
railway status

# View logs
railway logs
```

### Step 5: Get Your Bot URL
```bash
# Get your bot's public URL
railway domain
```

## Alternative: Deploy via Railway Dashboard

1. **Go to [Railway.app](https://railway.app)**
2. **Create New Project**
3. **Connect GitHub Repository** (if using git)
4. **Upload Files** manually:
   - `bot3.py`
   - `requirements.txt`
   - `railway.json`
   - `credentials/` folder
5. **Set Environment Variables** in the dashboard
6. **Deploy**

## Environment Variables in Railway Dashboard

Set these in your Railway project settings:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | Your Telegram bot token |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `ADMIN_ID` | Your Telegram user ID |
| `BOT_USERNAME` | Your bot's username |
| `GOOGLE_CREDENTIALS_PATH` | `./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json` |

## Monitoring Your Bot

```bash
# View real-time logs
railway logs --follow

# Check deployment status
railway status

# Restart bot if needed
railway service restart
```

## Troubleshooting

### Common Issues:
1. **Build Failures**: Check `requirements.txt` and Python version
2. **Environment Variables**: Ensure all required variables are set
3. **Credentials**: Verify Google Cloud credentials are uploaded
4. **Bot Token**: Confirm bot token is correct

### Debug Commands:
```bash
# Check Railway project info
railway whoami
railway projects

# View detailed logs
railway logs --tail 100

# SSH into Railway environment (if available)
railway shell
```

## Benefits of Railway

✅ **Free Tier Available**
✅ **Automatic Deployments**
✅ **Easy Environment Management**
✅ **Built-in Monitoring**
✅ **Global CDN**
✅ **SSL Certificates**
✅ **Custom Domains**

## Next Steps After Deployment

1. **Test Bot Commands**
2. **Monitor Logs**
3. **Set Up Alerts**
4. **Configure Custom Domain** (optional)
5. **Set Up Auto-Deploy** from Git (optional)


