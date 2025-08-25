# Fixes for bot3.py

# 1. FIX WATER REMINDER BUTTON
# Replace the send_water_reminder function with this version:
"""
async def send_water_reminder(user_id: int):
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        if not user_data.get('water_reminders', True):
            return
        lang = user_data.get('language', 'en')
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        now = datetime.now(tz)
        time_window = now - timedelta(hours=2)
        time_window_utc = time_window.astimezone(pytz.UTC)
        recent_water = list(get_water_ref(user_id).where('timestamp', '>=', time_window_utc).stream())
        if recent_water:
            logger.info(f"Skipping water reminder for user {user_id}: recent water logged")
            return
        message = t("water_reminder", lang)
        keyboard = get_water_keyboard(lang)  # Use existing water keyboard instead of custom one
        await bot.send_message(user_id, message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending water reminder to user {user_id}: {e}")
        if "chat not found" in str(e).lower():
            get_user_ref(user_id).update({'active': False})
            logger.info(f"Marked user {user_id} as inactive due to chat not found.")
"""

# 2. FIX ADMIN COMMAND - MOVE THESE BEFORE main() function
# Add these constants at the top of the file after other constants:
"""
ADMIN_ID = 5080813917
BOT_USERNAME = "BiteWiseBot"
"""

# Add this function before main():
"""
def get_admin_keyboard(lang='en'):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="User List (CSV)", callback_data="admin_export_users")],
            [InlineKeyboardButton(text="User Stats", callback_data="admin_user_stats")],
            [InlineKeyboardButton(text="Force Reschedule Reminders", callback_data="admin_force_reminders")]
        ]
    )
"""

# Add these handlers before main():
"""
@dp.message(lambda m: m.text and (m.text.strip().lower() == "/admin" or m.text.strip().lower() == f"/admin@{BOT_USERNAME.lower()}"), StateFilter(None))
@dp.message(lambda m: m.text and (m.text.strip().lower() == "/admin" or m.text.strip().lower() == f"/admin@{BOT_USERNAME.lower()}"), state='*')
async def admin_panel_universal(message: types.Message):
    print(f"[UNIVERSAL] /admin handler triggered by user {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔️ You are not authorized to use this command.")
        return
    text = (
        "🛠️ <b>Admin Panel</b>\n\n"
        "Choose an action below:\n"
        "• <b>User List (CSV)</b>: Export all users as a CSV file.\n"
        "• <b>User Stats</b>: Show user statistics.\n"
        "• <b>Force Reschedule Reminders</b>: Reschedule all reminders for all users."
    )
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)

@dp.callback_query(lambda c: c.data == "admin_export_users")
async def admin_export_users_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.answer()
    try:
        users = list(db.collection('users').stream())
        import csv
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', newline='', encoding='utf-8', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['telegram_id', 'telegram_username', 'name', 'age', 'goal', 'language', 'registered_at'])
            for u in users:
                d = u.to_dict()
                writer.writerow([
                    d.get('telegram_id', u.id),
                    d.get('telegram_username', ''),
                    d.get('name', ''),
                    d.get('age', ''),
                    d.get('goal', ''),
                    d.get('language', ''),
                    d.get('registered_at', '')
                ])
            f.flush()
            f.seek(0)
            await bot.send_document(callback.from_user.id, InputFile(f.name, filename='users.csv'))
    except Exception as e:
        await callback.message.answer(f"Error exporting users: {e}")

@dp.callback_query(lambda c: c.data == "admin_user_stats")
async def admin_user_stats_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.answer()
    try:
        users = list(db.collection('users').stream())
        total = len(users)
        active = sum(1 for u in users if u.to_dict().get('active', True))
        water_on = sum(1 for u in users if u.to_dict().get('water_reminders', True))
        meal_on = sum(1 for u in users if u.to_dict().get('meal_reminders', True))
        motivation_on = sum(1 for u in users if u.to_dict().get('motivational_quotes_enabled', True))
        await callback.message.answer(
            f"<b>User Stats</b>\nTotal: {total}\nActive: {active}\nWater Reminders: {water_on}\nMeal Reminders: {meal_on}\nMotivation: {motivation_on}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await callback.message.answer(f"Error getting stats: {e}")

@dp.callback_query(lambda c: c.data == "admin_force_reminders")
async def admin_force_reminders_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.answer("Rescheduling reminders for all users...")
    try:
        users = list(db.collection('users').stream())
        for u in users:
            d = u.to_dict()
            user_id = int(u.id)
            timezone = d.get('timezone', 'UTC')
            await schedule_default_reminders(user_id, timezone)
        await callback.message.answer("Reminders rescheduled for all users.")
    except Exception as e:
        await callback.message.answer(f"Error rescheduling reminders: {e}")
"""

# 3. FIX SCHEDULE_DEFAULT_REMINDERS - Replace the function with this version:
"""
async def schedule_default_reminders(user_id: int, timezone: str):
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        # Only skip if ALL reminder types are disabled
        water_disabled = user_data.get('water_reminders', True) is False
        meal_disabled = user_data.get('meal_reminders', True) is False
        motivation_disabled = user_data.get('motivational_quotes_enabled', True) is False
        breakfast_disabled = user_data.get('breakfast_reminder_enabled', True) is False
        lunch_disabled = user_data.get('lunch_reminder_enabled', True) is False
        dinner_disabled = user_data.get('dinner_reminder_enabled', True) is False
        
        # Only skip if ALL reminders are disabled
        if water_disabled and meal_disabled and motivation_disabled and breakfast_disabled and lunch_disabled and dinner_disabled:
            logger.info(f"Skipping reminders for user {user_id}: all reminders disabled")
            return
            
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Clear existing jobs for this user
        existing_jobs = [job for job in scheduler.get_jobs() if str(user_id) in job.id]
        for job in existing_jobs:
            job.remove()
        
        # Schedule water reminders (every 2 hours from 8 AM to 8 PM)
        if not water_disabled:
            for hour in range(8, 21, 2):  # 8, 10, 12, 14, 16, 18, 20
                reminder_time = tz.localize(datetime.combine(now.date(), time(hour, 0)))
                if reminder_time <= now:
                    reminder_time += timedelta(days=1)
                scheduler.add_job(
                    send_water_reminder,
                    'date',
                    run_date=reminder_time,
                    args=[user_id],
                    id=f"water_reminder_{user_id}_{hour}",
                    replace_existing=True
                )
                # Schedule recurring daily
                scheduler.add_job(
                    send_water_reminder,
                    'cron',
                    hour=hour,
                    minute=0,
                    timezone=timezone,
                    args=[user_id],
                    id=f"water_reminder_recurring_{user_id}_{hour}",
                    replace_existing=True
                )
        
        # Schedule meal reminders
        if not meal_disabled:
            meal_times = {
                'breakfast': (8, 0) if not breakfast_disabled else None,
                'lunch': (13, 0) if not lunch_disabled else None,
                'dinner': (19, 0) if not dinner_disabled else None
            }
            
            for meal_type, (hour, minute) in meal_times.items():
                if hour is not None:
                    reminder_time = tz.localize(datetime.combine(now.date(), time(hour, minute)))
                    if reminder_time <= now:
                        reminder_time += timedelta(days=1)
                    scheduler.add_job(
                        send_meal_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[user_id, meal_type],
                        id=f"meal_reminder_{user_id}_{meal_type}",
                        replace_existing=True
                    )
                    # Schedule recurring daily
                    scheduler.add_job(
                        send_meal_reminder,
                        'cron',
                        hour=hour,
                        minute=minute,
                        timezone=timezone,
                        args=[user_id, meal_type],
                        id=f"meal_reminder_recurring_{user_id}_{meal_type}",
                        replace_existing=True
                    )
        
        # Schedule motivational quotes (daily at 9 AM)
        if not motivation_disabled:
            motivation_time = tz.localize(datetime.combine(now.date(), time(9, 0)))
            if motivation_time <= now:
                motivation_time += timedelta(days=1)
            scheduler.add_job(
                send_motivational_quote,
                'date',
                run_date=motivation_time,
                args=[user_id],
                id=f"motivation_quote_{user_id}",
                replace_existing=True
            )
            # Schedule recurring daily
            scheduler.add_job(
                send_motivational_quote,
                'cron',
                hour=9,
                minute=0,
                timezone=timezone,
                args=[user_id],
                id=f"motivation_quote_recurring_{user_id}",
                replace_existing=True
            )
        
        # Schedule weekly summary (every Sunday at 8 PM)
        if not motivation_disabled:
            next_sunday = now + timedelta(days=(6 - now.weekday()) % 7)
            weekly_time = tz.localize(datetime.combine(next_sunday.date(), time(20, 0)))
            if weekly_time <= now:
                weekly_time += timedelta(days=7)
            scheduler.add_job(
                send_weekly_summary,
                'date',
                run_date=weekly_time,
                args=[user_id],
                id=f"weekly_summary_{user_id}",
                replace_existing=True
            )
            # Schedule recurring weekly
            scheduler.add_job(
                send_weekly_summary,
                'cron',
                day_of_week='sun',
                hour=20,
                minute=0,
                timezone=timezone,
                args=[user_id],
                id=f"weekly_summary_recurring_{user_id}",
                replace_existing=True
            )
        
        # Schedule weight update prompt (every 7 days at 10 AM)
        weight_time = tz.localize(datetime.combine(now.date(), time(10, 0)))
        if weight_time <= now:
            weight_time += timedelta(days=1)
        scheduler.add_job(
            send_weight_update_prompt,
            'date',
            run_date=weight_time,
            args=[user_id],
            id=f"weight_update_{user_id}",
            replace_existing=True
        )
        # Schedule recurring every 7 days
        scheduler.add_job(
            send_weight_update_prompt,
            'interval',
            days=7,
            timezone=timezone,
            args=[user_id],
            id=f"weight_update_recurring_{user_id}",
            replace_existing=True
        )
        
        logger.info(f"Scheduled reminders for user {user_id} in timezone {timezone}")
        
    except Exception as e:
        logger.error(f"Error scheduling reminders for user {user_id}: {e}")
"""

# 4. REMOVE DUPLICATE LINES
# Remove all the duplicate "@dp.message(F.text.lower() == "📊 mening statistikam")" lines
# Keep only one instance of each language variant.

# 5. DELETE THE ADMIN HANDLERS FROM THE END OF THE FILE
# Remove all the admin handlers that are placed after the main() function
# (lines 3101-3191 should be removed) 