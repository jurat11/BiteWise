# Bot Fix Instructions

## Issues Fixed:

### 1. **Reminders Not Working for Most Users**
**Problem:** The `schedule_default_reminders` function was skipping users with `active: False`
**Solution:** Replace the function with this version:

```python
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
        if all([water_disabled, meal_disabled, motivation_disabled, breakfast_disabled, lunch_disabled, dinner_disabled]):
            logger.info(f"Skipping scheduling for user {user_id}: all reminders disabled")
            return
            
        # Remove old jobs for this user
        for job in scheduler.get_jobs():
            parts = job.id.split('_')
            if len(parts) >= 2 and parts[1] == str(user_id):
                job.remove()
        # Handle invalid timezone gracefully
        try:
            tz = pytz.timezone(timezone)
        except Exception:
            logger.warning(f"Invalid timezone '{timezone}' for user {user_id}, falling back to UTC.")
            timezone = 'UTC'
            tz = pytz.UTC
        # Water reminders
        if user_data.get('water_reminders', True):
            water_times = [(8, 0), (10, 30), (13, 0), (15, 30), (18, 0), (20, 30)]
            for hour, minute in water_times:
                scheduler.add_job(
                    send_water_reminder,
                    'cron',
                    hour=hour,
                    minute=minute,
                    timezone=timezone,
                    args=[user_id],
                    id=f"water_{user_id}_{hour}_{minute}",
                    replace_existing=True,
                    misfire_grace_time=120
                )
                logger.info(f"Scheduled water reminder for user {user_id} at {hour:02d}:{minute:02d} {timezone}")
        # Meal reminders (main)
        if user_data.get('meal_reminders', True):
            meal_times = [("08:30", "breakfast"), ("13:00", "lunch"), ("19:00", "dinner")]
            for time, meal_type in meal_times:
                hour, minute = map(int, time.split(':'))
                scheduler.add_job(
                    send_meal_reminder,
                    'cron',
                    hour=hour,
                    minute=minute,
                    timezone=timezone,
                    args=[user_id, meal_type],
                    id=f"meal_{user_id}_{meal_type}",
                    replace_existing=True,
                    misfire_grace_time=120
                )
                logger.info(f"Scheduled {meal_type} reminder for user {user_id} at {hour:02d}:{minute:02d} {timezone}")
        # Motivational quote (personalized)
        if user_data.get('motivational_quotes_enabled', True):
            scheduler.add_job(
                send_motivational_quote,
                'cron',
                hour=21,
                minute=0,
                timezone=timezone,
                args=[user_id],
                id=f"motivation_{user_id}",
                replace_existing=True,
                misfire_grace_time=120
            )
            logger.info(f"Scheduled motivational quote for user {user_id} at 21:00 {timezone}")
        # Individual meal reminders (if enabled)
        if user_data.get('breakfast_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=8,
                minute=30,
                timezone=timezone,
                args=[user_id, 'breakfast'],
                id=f"breakfast_{user_id}",
                replace_existing=True,
                misfire_grace_time=120
            )
            logger.info(f"Scheduled breakfast reminder for user {user_id} at 08:30 {timezone}")
        if user_data.get('lunch_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=13,
                minute=0,
                timezone=timezone,
                args=[user_id, 'lunch'],
                id=f"lunch_{user_id}",
                replace_existing=True,
                misfire_grace_time=120
            )
            logger.info(f"Scheduled lunch reminder for user {user_id} at 13:00 {timezone}")
        if user_data.get('dinner_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=19,
                minute=0,
                timezone=timezone,
                args=[user_id, 'dinner'],
                id=f"dinner_{user_id}",
                replace_existing=True,
                misfire_grace_time=120
            )
            logger.info(f"Scheduled dinner reminder for user {user_id} at 19:00 {timezone}")
        # Weekly summary
        scheduler.add_job(
            send_weekly_summary,
            'cron',
            day_of_week='sun',
            hour=20,
            minute=0,
            timezone=timezone,
            args=[user_id],
            id=f"summary_{user_id}",
            replace_existing=True,
            misfire_grace_time=120
        )
        logger.info(f"Scheduled weekly summary for user {user_id} at Sunday 20:00 {timezone}")
        # Weight update (if goal is lose_weight)
        if user_data.get('goal') == "lose_weight":
            scheduler.add_job(
                send_weight_update_prompt,
                'cron',
                day_of_week='sun',
                hour=18,
                minute=0,
                timezone=timezone,
                args=[user_id],
                id=f"weight_update_{user_id}",
                replace_existing=True,
                misfire_grace_time=120
            )
            logger.info(f"Scheduled weight update prompt for user {user_id} at Sunday 18:00 {timezone}")
        logger.info(f"Scheduled ALL reminders for user {user_id} (timezone: {timezone}). Total jobs now: {len(scheduler.get_jobs())}")
    except Exception as e:
        logger.error(f"Error scheduling reminders for user {user_id}: {e}")
```

### 2. **Motivational Quotes Using Wrong Names**
**Problem:** AI was translating user names
**Solution:** Update the `send_motivational_quote` function:

```python
async def send_motivational_quote(user_id: int):
    try:
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()
        if not user_data.get('motivational_quotes_enabled', True):
            return
        lang = user_data.get('language', 'en')
        goal = user_data.get('goal', 'other_goal')
        user_name = user_data.get('name', 'User')  # Use original name as-is
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(tz).date()
        today_start = tz.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
        today_end = tz.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)
        meals_ref = get_meals_ref(user_id)
        today_meal_docs = list(
            meals_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_calories = sum(m.to_dict().get('calories', 0) for m in today_meal_docs)
        water_ref = get_water_ref(user_id)
        today_water_docs = list(
            water_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_water = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)
        day_of_year = today.timetuple().tm_yday
        themes = [
            t("benefit", lang),
            t("recommendation", lang),
            t("health_note", lang),
            t("streaks", lang),
            t("main_menu", lang)
        ]
        theme = themes[day_of_year % len(themes)]
        prompt = (
            f"Write a motivational message in {lang} for {user_name} (goal: {t(goal, lang)}). "
            f"Today: {today_calories} kcal, {today_water} ml water. "
            f"Theme: {theme}. "
            f"Make it 2 sentences, use 2 emojis, and be personal. "
            f"IMPORTANT: Use the name '{user_name}' exactly as provided - do not translate or change it."
        )
        try:
            response = nutrition_model.generate_content(prompt)
            quote = response.text.strip()
            quote = ' '.join(quote.split('.')[:2]).strip() + ('.' if not quote.endswith('.') else '')
        except Exception as e:
            logger.error(f"Failed to generate quote for user {user_id}: {e}")
            quote = (f"{user_name}, {t('default_motivational_quote', lang)} "
                     f"({today_calories} kcal, {today_water} ml)")
        await bot.send_message(
            user_id,
            f"══════════════\n{user_name}, {quote}\n══════════════",
            reply_markup=get_main_menu_keyboard(lang)
        )
    except Exception as e:
        logger.error(f"Error sending motivational quote to user {user_id}: {e}")
        if "chat not found" in str(e).lower():
            get_user_ref(user_id).update({'active': False})
            logger.info(f"Marked user {user_id} as inactive due to chat not found.")
```

### 3. **Admin Panel Not Working**
**Problem:** Admin handlers were placed after `main()` function
**Solution:** Add these constants at the top of the file (after the existing configuration):

```python
ADMIN_ID = 5080813917
BOT_USERNAME = "BiteWiseBot"  # Replace with your bot's username (without @)
```

And add these admin handlers **BEFORE** the `main()` function:

```python
# Admin Panel Functions
def get_admin_keyboard(lang='en'):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="User List (CSV)", callback_data="admin_export_users")],
            [InlineKeyboardButton(text="User Stats", callback_data="admin_user_stats")],
            [InlineKeyboardButton(text="Force Reschedule Reminders", callback_data="admin_force_reminders")]
        ]
    )

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
```

## Steps to Apply:

1. **Add the constants** at the top of your file
2. **Replace the `schedule_default_reminders` function** with the new version
3. **Replace the `send_motivational_quote` function** with the new version  
4. **Add the admin handlers** before the `main()` function
5. **Remove any duplicate admin handlers** that are after the `main()` function
6. **Remove duplicate lines** in the show_stats function (there are many duplicate `@dp.message(F.text.lower() == "📊 mening statistikam")` lines)

After making these changes, your bot will:
- Send reminders to ALL users unless they explicitly disable ALL reminder types
- Use the user's original name in motivational quotes without translation
- Have a working admin panel with `/admin` command 