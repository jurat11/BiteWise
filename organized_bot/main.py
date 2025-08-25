import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database.db import db
from handlers import (
    register_start_handlers,
    register_water_handlers,
    register_meal_handlers,
    register_stats_handlers,
    register_settings_handlers,
    register_help_handlers
)
from utils.reminders import setup_reminders

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register all handlers
def register_all_handlers():
    register_start_handlers(dp)
    register_water_handlers(dp)
    register_meal_handlers(dp)
    register_stats_handlers(dp)
    register_settings_handlers(dp)
    register_help_handlers(dp)

async def main():
    try:
        # Initialize scheduler
        scheduler = AsyncIOScheduler()
        
        # Setup reminders
        setup_reminders(scheduler, bot)
        scheduler.start()
        
        # Register handlers
        register_all_handlers()
        
        # Start polling
        logger.info("Bot is starting...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        # Shutdown
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main()) 