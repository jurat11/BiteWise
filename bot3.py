
import os
import asyncio
import logging
import re
import traceback
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, 
    KeyboardButton, InputFile
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Google Cloud imports
try:
    from google.cloud import firestore
    from google.oauth2 import service_account
    import google.generativeai as genai
    import pytz
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7189930971:AAEZ4LUYS5lLTotI4ec2W1YmS1CI3CmVmNY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5080813917"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "@BiteWiseBot")

# Initialize Firestore
try:
    if GOOGLE_CREDENTIALS_PATH and os.path.exists(GOOGLE_CREDENTIALS_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH
        db = firestore.Client()
    else:
        # For Railway deployment, try to use default credentials
        try:
            db = firestore.Client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore with default credentials: {e}")
            # Create a mock database for testing
            db = None
            logger.warning("Running without database - some features will be limited")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    # For Railway deployment, continue without database
    db = None
    logger.warning("Running without database - some features will be limited")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    nutrition_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")

def get_user_ref(user_id: int):
    if db is None:
        logger.warning("Database not available - cannot get user reference")
        return None
    return db.collection('users').document(str(user_id))

def get_meals_ref(user_id: int):
    user_ref = get_user_ref(user_id)
    if user_ref is None:
        return None
    return user_ref.collection('meals')

def get_water_ref(user_id: int):
    user_ref = get_user_ref(user_id)
    if user_ref is None:
        return None
    return user_ref.collection('water')

def get_streaks_ref(user_id: int):
    user_ref = get_user_ref(user_id)
    if user_ref is None:
        return None
    return user_ref.collection('streaks')

# Bot Setup
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# States
class SettingsStates(StatesGroup):
    changing_language = State()
    editing_profile = State()
    editing_reminders = State()

class EditProfileStates(StatesGroup):
    selecting_field = State()
    editing_name = State()
    editing_age = State()
    editing_height = State()
    editing_weight = State()

class EditRemindersStates(StatesGroup):
    main_menu = State()

class Registration(StatesGroup):
    language = State()
    name = State()
    age = State()
    height = State()
    weight = State()
    gender = State()
    timezone = State()
    goal = State()
    activity_level = State()

class ReminderStates(StatesGroup):
    setting_water = State()
    setting_meal = State()

class MealLogging(StatesGroup):
    selecting_type = State()
    waiting_for_text = State()
    waiting_for_note = State()

class WeightUpdateStates(StatesGroup):
    waiting_for_weight = State()

class WaterLogging(StatesGroup):
    waiting_for_custom = State()

# Helper Functions
async def get_user_language(user_id: int) -> str:
    try:
        user_ref = get_user_ref(user_id)
        if user_ref is None:
            return 'en'  # Default to English if database not available
        doc = user_ref.get()
        return doc.to_dict().get('language', 'en') if doc.exists else 'en'
    except Exception as e:
        logger.error(f"Language fetch failed for user {user_id}: {e}")
        return 'en'

def create_mock_user_data(user_id: int, name: str = None):
    """Create mock user data when database is not available"""
    return {
        'user_id': user_id,
        'name': name or f"User{user_id}",
        'language': 'en',
        'height': 'Not set',
        'weight': 'Not set',
        'goal': 'Not set',
        'created_at': datetime.now(pytz.utc),
        'last_active': datetime.now(pytz.utc)
    }

# Mock database for when Firestore is not available
mock_users = {}

# Keyboard Functions
def get_language_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set_lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")]
    ])

def get_main_menu_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Log Meal"), KeyboardButton(text="💧 Log Water")],
            [KeyboardButton(text="📊 My Stats"), KeyboardButton(text="⚖️ Update Weight")],
            [KeyboardButton(text="⚙️ Settings"), KeyboardButton(text="📚 Help")]
        ],
        resize_keyboard=True
    )

# Handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    
    if db is None:
        # Database not available, use mock data
        if user_id not in mock_users:
            mock_users[user_id] = create_mock_user_data(user_id, message.from_user.first_name)
        await message.answer("Welcome to BiteWise! Please select your language:", reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)
    elif user_ref is None:
        # Database not available, treat as new user
        await message.answer("Welcome to BiteWise! Please select your language:", reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)
    elif user_ref.get().exists:
        lang = await get_user_language(user_id)
        await message.answer(f"Welcome back! You're already registered.", reply_markup=get_main_menu_keyboard(lang))
    else:
        await message.answer("Welcome to BiteWise! Please select your language:", reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)

@dp.message(F.text.lower() == "💧 log water")
@dp.message(Command("water"))
async def log_water(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # Update last active if database is available
    user_ref = get_user_ref(user_id)
    if user_ref is not None:
        try:
            user_ref.update({'last_active': datetime.now(pytz.utc)})
        except Exception as e:
            logger.warning(f"Failed to update last_active for user {user_id}: {e}")
    elif db is None:
        # Update mock data
        if user_id in mock_users:
            mock_users[user_id]['last_active'] = datetime.now(pytz.utc)
    
    await message.answer("Select water amount:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100ml", callback_data="water_100")],
        [InlineKeyboardButton(text="250ml", callback_data="water_250")],
        [InlineKeyboardButton(text="500ml", callback_data="water_500")],
        [InlineKeyboardButton(text="Custom", callback_data="water_custom")]
    ]))

@dp.message(F.text.lower() == "📊 my stats")
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)
        
        # Check if database is available
        if db is None:
            # Use mock data when database is not available
            if user_id not in mock_users:
                mock_users[user_id] = create_mock_user_data(user_id, message.from_user.first_name)
            user_data = mock_users[user_id]
            
            response = f"📊 <b>Your Stats (Demo Mode):</b>\n\n"
            response += f"👤 <b>Name:</b> {user_data.get('name', 'Not set')}\n"
            response += f"📏 <b>Height:</b> {user_data.get('height', 'Not set')}\n"
            response += f"⚖️ <b>Weight:</b> {user_data.get('weight', 'Not set')}\n"
            response += f"🎯 <b>Goal:</b> {user_data.get('goal', 'Not set')}\n"
            response += f"🌍 <b>Language:</b> {user_data.get('language', 'en')}\n"
            response += f"\n⚠️ <i>Running in demo mode - data not saved</i>"
            
            await message.answer(response, reply_markup=get_main_menu_keyboard(lang))
            return
            
        user_ref = get_user_ref(user_id)
        if user_ref is None:
            await message.answer("❌ Cannot access user data", reply_markup=get_main_menu_keyboard(lang))
            return
            
        # Get user data safely
        try:
            user_data = user_ref.get().to_dict()
            if not user_data:
                await message.answer("❌ User data not found", reply_markup=get_main_menu_keyboard(lang))
                return
        except Exception as e:
            logger.error(f"Failed to get user data for {user_id}: {e}")
            await message.answer("❌ Error accessing user data", reply_markup=get_main_menu_keyboard(lang))
            return
            
        # Show basic stats
        response = f"📊 <b>Your Stats:</b>\n\n"
        response += f"👤 <b>Name:</b> {user_data.get('name', 'Not set')}\n"
        response += f"📏 <b>Height:</b> {user_data.get('height', 'Not set')} cm\n"
        response += f"⚖️ <b>Weight:</b> {user_data.get('weight', 'Not set')} kg\n"
        response += f"🎯 <b>Goal:</b> {user_data.get('goal', 'Not set')}\n"
        response += f"🌍 <b>Language:</b> {user_data.get('language', 'en')}\n"
        
        await message.answer(response, reply_markup=get_main_menu_keyboard(lang))
        
    except Exception as e:
        logger.error(f"Stats error for user {message.from_user.id}: {e}")
        await message.answer("❌ Error showing stats", reply_markup=get_main_menu_keyboard('en'))

@dp.message(F.text.lower() == "🍽 log meal")
async def log_meal_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # Check if database is available
    if db is None:
        await message.answer("❌ Database not available - cannot log meals", reply_markup=get_main_menu_keyboard(lang))
        return
        
    await message.answer("Please enter the food name:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Back")]],
        resize_keyboard=True
    ))
    await state.set_state(MealLogging.waiting_for_text)

@dp.message(MealLogging.waiting_for_text, F.text)
async def process_meal_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if message.text.strip().lower() == "🔙 back":
        await message.answer("Back to main menu", reply_markup=get_main_menu_keyboard(lang))
        await state.clear()
        return
        
    try:
        text = message.text.strip()
        if not text:
            raise ValueError("Empty text input")

        logger.info(f"Processing meal text for user {user_id}: {text}")
        
        # Get user data safely
        user_ref = get_user_ref(user_id)
        if user_ref is None:
            await message.answer("❌ Cannot access user data", reply_markup=get_main_menu_keyboard(lang))
            await state.clear()
            return
            
        try:
            user_data = user_ref.get().to_dict()
            daily_calories = user_data.get('daily_calories', 2000)
        except Exception as e:
            logger.warning(f"Failed to get user data for {user_id}: {e}")
            daily_calories = 2000

        # Create prompt for AI
        prompt = f"Provide nutritional information for {text} in this format:\n"
        prompt += f"- Calories: [value] kcal\n"
        prompt += f"- Protein: [value]g\n"
        prompt += f"- Carbs: [value]g\n"
        prompt += f"- Fat: [value]g\n"
        prompt += f"- Sodium: [value]mg\n"
        prompt += f"- Fiber: [value]g\n"
        prompt += f"- Sugar: [value]g\n\n"
        prompt += f"Use {daily_calories} kcal as daily calorie need for percentage calculation."

        # Get AI response
        try:
            response = nutrition_model.generate_content(prompt)
            analysis = response.text.strip()
        except Exception as e:
            logger.error(f"AI response failed for user {user_id}: {e}")
            analysis = f"❌ Failed to analyze {text}. Please try again."

        # Log meal if database is available
        meals_ref = get_meals_ref(user_id)
        if meals_ref is not None:
            try:
                meal_ref = meals_ref.add({
                    'timestamp': datetime.now(pytz.utc),
                    'analysis': analysis,
                    'text_input': text,
                    'meal_type': 'meal',
                    'calories': 0,  # Default values
                    'protein': 0,
                    'carbs': 0,
                    'fat': 0,
                    'sodium': 0,
                    'fiber': 0,
                    'sugar': 0
                })
                logger.info(f"Meal logged for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to log meal for user {user_id}: {e}")
        else:
            logger.warning(f"Database not available - meal not logged for user {user_id}")

        await message.answer(analysis, reply_markup=get_main_menu_keyboard(lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Text processing error for user {user_id}: {e}")
        await message.answer("❌ Error processing meal", reply_markup=get_main_menu_keyboard(lang))
        await state.clear()

# Water logging callbacks
@dp.callback_query(lambda c: c.data.startswith('water_'))
async def process_water_callback(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        lang = await get_user_language(user_id)
        
        if callback_query.data == "water_custom":
            await callback_query.message.answer("Please enter the amount of water in ml:")
            # You can implement custom water input here
        else:
            amount = callback_query.data.replace('water_', '')
            if db is None:
                # Mock water logging
                await callback_query.message.answer(f"💧 Logged {amount}ml of water! (Demo mode - not saved)")
            else:
                # Real water logging
                water_ref = get_water_ref(user_id)
                if water_ref is not None:
                    try:
                        water_ref.add({
                            'amount': int(amount),
                            'timestamp': datetime.now(pytz.utc)
                        })
                        await callback_query.message.answer(f"💧 Logged {amount}ml of water!")
                    except Exception as e:
                        logger.error(f"Failed to log water for user {user_id}: {e}")
                        await callback_query.message.answer("❌ Failed to log water")
                else:
                    await callback_query.message.answer("❌ Cannot access water data")
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Water callback error: {e}")
        await callback_query.answer("❌ Error processing water log")

# Main execution
async def main():
    scheduler.start()
    # Schedule reminders for all users on startup (await, not create_task)
    if db is None:
        logger.warning("Database not available - skipping startup reminder scheduling")
        logger.info("Bot starting without database - basic functionality will work")
    else:
        try:
            all_users = list(db.collection('users').stream())
            for user_doc in all_users:
                user_data = user_doc.to_dict()
                user_id = int(user_doc.id)
                timezone = user_data.get('timezone', 'UTC')
                try:
                    # Schedule reminders if function exists
                    pass
                except Exception as e:
                    logger.error(f"Failed to schedule reminders for user {user_id} on startup: {e}")
                await asyncio.sleep(0.01)  # Small delay to avoid CPU spike
        except Exception as e:
            logger.error(f"Failed to load users on startup: {e}")
            logger.warning("Continuing without user data")
    
    logger.info(f"Total jobs after startup: {len(scheduler.get_jobs())}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
