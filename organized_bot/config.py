import os
from pathlib import Path

# Bot token
BOT_TOKEN = "8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"
ADMIN_ID = 5080813917

# Project paths
BASE_DIR = Path(__file__).parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# Google Cloud credentials
GOOGLE_CREDENTIALS_PATH = str(CREDENTIALS_DIR / "sturdy-lead-454406-n3-16c47cb3a35a.json")
GEMINI_API_KEY = "AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY"

# Reminder times (24-hour format)
REMINDER_TIMES = {
    'breakfast': '08:00',
    'lunch': '13:00',
    'dinner': '19:00',
    'motivation': '21:00',
    'weekly_summary': 'sunday 20:00'
}

# Water logging limits
MIN_WATER_AMOUNT = 1
MAX_WATER_AMOUNT = 5000
WATER_COOLDOWN_MINUTES = 5

# Supported languages
SUPPORTED_LANGUAGES = ['en', 'ru', 'uz']
DEFAULT_LANGUAGE = 'en'

# Database collections
USERS_COLLECTION = 'users'
MEALS_COLLECTION = 'meals'
WATER_COLLECTION = 'water'
STREAKS_COLLECTION = 'streaks' 