import os
import asyncio
import logging
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Bot token
BOT_TOKEN = "8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Simple keyboard layouts
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

# Command handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Welcome to BiteWise! Choose an option:",
        reply_markup=get_main_keyboard()
    )

# Button handlers
@dp.message(lambda message: message.text == "🍽 Log Meal")
async def handle_log_meal(message: types.Message):
    await message.answer(
        "This feature is coming soon!",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "💧 Log Water")
async def handle_log_water(message: types.Message):
    await message.answer(
        "Select water amount:",
        reply_markup=get_water_keyboard()
    )

@dp.message(lambda message: message.text == "📊 My Stats")
async def handle_stats(message: types.Message):
    await message.answer(
        "Your stats will be shown here!",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "⚙️ Settings")
async def handle_settings(message: types.Message):
    await message.answer(
        "Settings menu coming soon!",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "❓ Help")
async def handle_help(message: types.Message):
    await message.answer(
        "Need help? Contact @admin",
        reply_markup=get_main_keyboard()
    )

# Water amount handler
@dp.message(lambda message: message.text in ["250 ml", "500 ml", "750 ml", "1000 ml"])
async def handle_water_amount(message: types.Message):
    amount = int(message.text.split()[0])
    await message.answer(
        f"✅ Logged {amount}ml of water!",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda message: message.text == "❌ Cancel")
async def handle_cancel(message: types.Message):
    await message.answer(
        "Action canceled",
        reply_markup=get_main_keyboard()
    )

# Main execution
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 