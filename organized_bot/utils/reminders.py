import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from organized_bot.config import REMINDER_TIMES
from organized_bot.database.db import db

logger = logging.getLogger(__name__)

async def send_reminder(bot: Bot, user_id: int, text: str):
    try:
        await bot.send_message(chat_id=user_id, text=text)
        logger.info(f"Sent reminder to user {user_id}: {text}")
    except Exception as e:
        logger.error(f"Failed to send reminder to user {user_id}: {e}")

async def send_weekly_summary(bot: Bot, user_id: int):
    # Placeholder: implement actual summary logic as needed
    await send_reminder(bot, user_id, "📊 Your weekly summary is ready! (feature coming soon)")

def setup_reminders(scheduler, bot: Bot):
    users_ref = db.collection('users')
    try:
        users = list(users_ref.stream())
    except Exception as e:
        logger.error(f"Failed to fetch users for reminders: {e}")
        return
    for user_doc in users:
        user = user_doc.to_dict()
        user_id = int(user_doc.id)
        timezone = user.get('timezone', 'UTC')
        lang = user.get('language', 'en')
        # Water reminders (every 2 hours 8:00-20:00)
        if user.get('water_reminders', True):
            for hour in range(8, 22, 2):
                scheduler.add_job(
                    send_reminder,
                    CronTrigger(hour=hour, minute=0, timezone=timezone),
                    args=[bot, user_id, "💧 Time to drink water!"],
                    id=f"water_{user_id}_{hour}",
                    replace_existing=True
                )
        # Meal reminders
        if user.get('meal_reminders', True):
            for meal in ['breakfast', 'lunch', 'dinner']:
                time_str = REMINDER_TIMES[meal]
                hour, minute = map(int, time_str.split(':'))
                scheduler.add_job(
                    send_reminder,
                    CronTrigger(hour=hour, minute=minute, timezone=timezone),
                    args=[bot, user_id, f"🍽 Time for {meal.capitalize()}!"],
                    id=f"meal_{user_id}_{meal}",
                    replace_existing=True
                )
        # Motivation reminder
        if user.get('motivational_quotes_enabled', True):
            hour, minute = map(int, REMINDER_TIMES['motivation'].split(':'))
            scheduler.add_job(
                send_reminder,
                CronTrigger(hour=hour, minute=minute, timezone=timezone),
                args=[bot, user_id, "💡 Stay motivated! Here's your daily quote!"],
                id=f"motivation_{user_id}",
                replace_existing=True
            )
        # Weekly summary (Sunday 20:00)
        hour, minute = map(int, REMINDER_TIMES['weekly_summary'].split()[1].split(':'))
        scheduler.add_job(
            send_weekly_summary,
            CronTrigger(day_of_week='sun', hour=hour, minute=minute, timezone=timezone),
            args=[bot, user_id],
            id=f"weekly_summary_{user_id}",
            replace_existing=True
        )
        logger.info(f"Scheduled all reminders for user {user_id} in timezone {timezone}") 