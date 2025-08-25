import os
import asyncio
import logging
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from google.cloud import firestore

# Bot token
BOT_TOKEN = "8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore
try:
    db = firestore.Client()
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client()

# States
class UserStates(StatesGroup):
    WATER_AMOUNT = State()
    MEAL_TYPE = State()
    MEAL_DESCRIPTION = State()

# Database functions
def get_user_ref(user_id: int):
    return db.collection('users').document(str(user_id))

def get_meals_ref(user_id: int):
    return get_user_ref(user_id).collection('meals')

def get_water_ref(user_id: int):
    return get_user_ref(user_id).collection('water')

# Keyboard layouts
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🍽 Log Meal"), KeyboardButton(text="💧 Log Water")],
        [KeyboardButton(text="📊 My Stats"), KeyboardButton(text="⚙️ Settings")],
        [KeyboardButton(text="❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_water_keyboard():
    keyboard = [
        [KeyboardButton(text="250 ml"), KeyboardButton(text="500 ml")],
        [KeyboardButton(text="750 ml"), KeyboardButton(text="1000 ml")],
        [KeyboardButton(text="❌ Cancel")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_meal_keyboard():
    keyboard = [
        [KeyboardButton(text="🍳 Breakfast"), KeyboardButton(text="🥗 Lunch")],
        [KeyboardButton(text="🍽 Dinner"), KeyboardButton(text="🍪 Snack")],
        [KeyboardButton(text="❌ Cancel")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Bot setup
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Command handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    
    # Create or update user document
    user_ref.set({
        'user_id': user_id,
        'last_active': datetime.now(pytz.UTC)
    }, merge=True)
    
    await message.answer(
        "👋 Welcome to BiteWise! Choose an option:",
        reply_markup=get_main_keyboard()
    )

# Button handlers
@dp.message(lambda message: message.text == "🍽 Log Meal")
async def handle_log_meal(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.MEAL_TYPE)
    await message.answer(
        "Select meal type:",
        reply_markup=get_meal_keyboard()
    )

@dp.message(lambda message: message.text == "💧 Log Water")
async def handle_log_water(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.WATER_AMOUNT)
    await message.answer(
        "Select water amount:",
        reply_markup=get_water_keyboard()
    )

@dp.message(lambda message: message.text == "📊 My Stats")
async def handle_stats(message: types.Message):
    try:
        user_id = message.from_user.id
        
        # Get water stats
        water_ref = get_water_ref(user_id)
        today_start = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_water = sum(w.to_dict().get('amount', 0) for w in 
                         water_ref.where('timestamp', '>=', today_start).stream())
        
        # Get meal stats
        meals_ref = get_meals_ref(user_id)
        today_meals = list(meals_ref.where('timestamp', '>=', today_start).stream())
        
        stats_message = (
            "📊 Your Stats\n\n"
            f"💧 Water today: {today_water}ml\n"
            f"🍽 Meals today: {len(today_meals)}"
        )
        
        await message.answer(stats_message, reply_markup=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await message.answer("Error processing request")

@dp.message(lambda message: message.text == "⚙️ Settings")
async def handle_settings(message: types.Message):
    await message.answer(
        "Settings menu coming soon!",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "❓ Help")
async def handle_help(message: types.Message):
    help_text = (
        "🌟 Welcome to BiteWise!\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/water - Log water intake\n"
        "/stats - View your statistics\n"
        "/settings - Access settings\n\n"
        "For more help, contact @admin"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

# State handlers
@dp.message(UserStates.WATER_AMOUNT)
async def process_water_amount(message: types.Message, state: FSMContext):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer(
            "Action canceled",
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        # Handle predefined amounts
        if message.text in ["250 ml", "500 ml", "750 ml", "1000 ml"]:
            amount = int(message.text.split()[0])
        else:
            # Handle custom amount
            amount = int(message.text)
            
        if amount < 1 or amount > 5000:
            raise ValueError()
            
        # Log water intake
        water_ref = get_water_ref(message.from_user.id)
        water_ref.add({
            'amount': amount,
            'timestamp': datetime.now(pytz.UTC)
        })
        
        await message.answer(
            f"✅ Logged {amount}ml of water!",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Please enter a valid amount between 1 and 5000 ml",
            reply_markup=get_water_keyboard()
        )

@dp.message(UserStates.MEAL_TYPE)
async def process_meal_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer(
            "Action canceled",
            reply_markup=get_main_keyboard()
        )
        return
        
    valid_types = ["🍳 Breakfast", "🥗 Lunch", "🍽 Dinner", "🍪 Snack"]
    if message.text not in valid_types:
        await message.answer(
            "Please select a valid meal type",
            reply_markup=get_meal_keyboard()
        )
        return
        
    await state.update_data(meal_type=message.text)
    await state.set_state(UserStates.MEAL_DESCRIPTION)
    await message.answer(
        "Please describe what you ate:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(UserStates.MEAL_DESCRIPTION)
async def process_meal_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    meal_type = data.get('meal_type')
    
    # Log meal
    meals_ref = get_meals_ref(message.from_user.id)
    meals_ref.add({
        'type': meal_type,
        'description': message.text,
        'timestamp': datetime.now(pytz.UTC)
    })
    
    await message.answer(
        f"✅ {meal_type} logged!",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# Main execution
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 