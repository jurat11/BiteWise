import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from google.cloud import firestore
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import io

# ==================== Project Directory Setup ====================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_DIR = os.path.join(PROJECT_DIR, "credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# ==================== Translations ====================

TRANSLATIONS = {
    "intro": {
        "en": "👋 Hello! I am NutritionBot. Please select your language:",
        "ru": "👋 Привет! Я NutritionBot. Пожалуйста, выберите язык:",
        "uz": "👋 Salom! Men NutritionBot. Tilni tanlang:"
    },
    "select_language": {
        "en": "Choose your language:",
        "ru": "Выберите ваш язык:",
        "uz": "Tilni tanlang:"
    },
    "ask_name": {
        "en": "Enter your name:",
        "ru": "Введите ваше имя:",
        "uz": "Ismingizni kiriting:"
    },
    "name_error": {
        "en": "Name should be between 2 and 50 characters.",
        "ru": "Имя должно быть от 2 до 50 символов.",
        "uz": "Ism 2 dan 50 belgigacha bo'lishi kerak."
    },
    "ask_age": {
        "en": "Enter your age:",
        "ru": "Введите ваш возраст:",
        "uz": "Yoshingizni kiriting:"
    },
    "age_error": {
        "en": "Please enter a valid age between 0 and 120",
        "ru": "Введите правильный возраст от 0 до 120",
        "uz": "Iltimos, 0 dan 120 gacha yoshingizni kiriting"
    },
    "ask_height": {
        "en": "Enter your height (cm):",
        "ru": "Введите ваш рост (см):",
        "uz": "Bo'yingizni kiriting (sm):"
    },
    "height_error": {
        "en": "Please enter a valid height between 50 and 250 cm",
        "ru": "Введите правильный рост от 50 до 250 см",
        "uz": "Iltimos, 50 dan 250 sm gacha bo'yingizni kiriting"
    },
    "ask_weight": {
        "en": "Enter your weight (kg):",
        "ru": "Введите ваш вес (кг):",
        "uz": "Vazningizni kiriting (kg):"
    },
    "weight_error": {
        "en": "Please enter a valid weight between 20 and 300 kg",
        "ru": "Введите правильный вес от 20 до 300 кг",
        "uz": "Iltimos, 20 dan 300 kg gacha vazningizni kiriting"
    },
    "ask_gender": {
        "en": "Select your gender:",
        "ru": "Выберите ваш пол:",
        "uz": "Jinsingizni tanlang:"
    },
    "ask_timezone": {
        "en": "Select or enter your timezone:",
        "ru": "Выберите или введите ваш часовой пояс:",
        "uz": "Vaqt mintaqangizni tanlang yoki kiriting:"
    },
    "timezone_error": {
        "en": "Invalid timezone. Please select one from the buttons or enter a valid timezone",
        "ru": "Неверный часовой пояс. Выберите из кнопок или введите правильный часовой пояс",
        "uz": "Noto'g'ri vaqt mintaqasi. Tugmalardan tanlang yoki to'g'ri vaqt mintaqasini kiriting"
    },
    "ask_goal": {
        "en": "(Optional) Select or enter your goal:",
        "ru": "(Необязательно) Выберите или введите вашу цель:",
        "uz": "(Ixtiyoriy) Maqsadingizni tanlang yoki kiriting:"
    },
    "registration_complete": {
        "en": "✅ Registration complete! Send me food info or photos.",
        "ru": "✅ Регистрация завершена! Отправьте информацию о еде.",
        "uz": "✅ Ro'yxatdan o'tish yakunlandi! Ovqat haqida ma'lumot yuboring."
    },
    "water_reminder": {
        "en": "💧 Time to drink water! Stay hydrated!",
        "ru": "💧 Время пить воду! Поддерживайте водный баланс!",
        "uz": "💧 Suv ichish vaqti! Suv miqdorini saqlang!"
    },
    "meal_reminder": {
        "en": "⏰ Don't forget to log your meal!",
        "ru": "⏰ Не забудьте записать свой прием пищи!",
        "uz": "⏰ Ovqatlanishingizni kiritishni unutmang!"
    },
    "reminder_set": {
        "en": "⏰ Reminder set successfully for {time}",
        "ru": "⏰ Напоминание успешно установлено на {time}",
        "uz": "⏰ Eslatma {time} da muvaffaqiyatli o'rnatildi"
    },
    "water_logged": {
        "en": "✅ Water intake recorded! +250ml",
        "ru": "✅ Прием воды зарегистрирован! +250мл",
        "uz": "✅ Suv miqdori qayd etildi! +250ml"
    },
    "processing": {
        "en": "⏳ Processing your request...",
        "ru": "⏳ Обрабатываю ваш запрос...",
        "uz": "⏳ So'rovingiz bajarilmoqda..."
    },
    "error_processing": {
        "en": "❌ Error processing your request. Please try again.",
        "ru": "❌ Ошибка при обработке запроса. Пожалуйста, попробуйте снова.",
        "uz": "❌ So'rovni qayta ishlashda xatolik. Iltimos, qaytadan urinib ko'ring."
    },
    "main_menu": {
        "en": "📋 Main Menu - What would you like to do?",
        "ru": "📋 Главное меню - Что бы вы хотели сделать?",
        "uz": "📋 Asosiy menyu - Nima qilmoqchisiz?"
    },
    "menu_log_water": {
        "en": "💧 Log Water",
        "ru": "💧 Записать воду",
        "uz": "💧 Suv qayd etish"
    },
    "menu_stats": {
        "en": "📊 My Stats",
        "ru": "📊 Моя статистика",
        "uz": "📊 Mening statistikam"
    },
    "menu_settings": {
        "en": "⚙️ Settings",
        "ru": "⚙️ Настройки",
        "uz": "⚙️ Sozlamalar"
    },
    "menu_log_meal": {
        "en": "🍽 Log Meal",
        "ru": "🍽 Записать прием пищи",
        "uz": "🍽 Ovqat qayd etish"
    },
    "menu_help": {
        "en": "❓ Help",
        "ru": "❓ Помощь",
        "uz": "❓ Yordam"
    },
    "help_text": {
        "en": "🌟 <b>How to Use NutritionBot:</b>\n\n"
              "• <b>Log Meals:</b> Send a photo of your food or text describing what you ate\n"
              "• <b>Log Water:</b> Use the 💧 button or /water command\n"
              "• <b>View Stats:</b> Use the 📊 button or /stats command\n"
              "• <b>Main Menu:</b> Use /menu command anytime\n\n"
              "For more assistance, contact @support_handle",
        "ru": "🌟 <b>Как использовать NutritionBot:</b>\n\n"
              "• <b>Запись питания:</b> Отправьте фото еды или текст с описанием\n"
              "• <b>Запись воды:</b> Используйте кнопку 💧 или команду /water \n"
              "• <b>Просмотр статистики:</b> Используйте кнопку 📊 или команду /stats\n"
              "• <b>Главное меню:</b> Используйте команду /menu в любой момент\n\n"
              "Для дополнительной помощи обратитесь к @support_handle",
        "uz": "🌟 <b>NutritionBot-dan qanday foydalanish mumkin:</b>\n\n"
              "• <b>Ovqatni qayd etish:</b> Ovqatning rasmini yoki tavsifini yuboring\n"
              "• <b>Suvni qayd etish:</b> 💧 tugmasini yoki /water buyrug'ini ishlating\n"
              "• <b>Statistikani ko'rish:</b> 📊 tugmasini yoki /stats buyrug'ini ishlating\n"
              "• <b>Asosiy menyu:</b> Istalgan vaqtda /menu buyrug'ini ishlating\n\n"
              "Qo'shimcha yordam uchun @support_handle ga murojaat qiling"
    },
    "male": {
        "en": "Male",
        "ru": "Мужской",
        "uz": "Erkak"
    },
    "female": {
        "en": "Female",
        "ru": "Женский",
        "uz": "Ayol"
    }
}


def t(key: str, lang: str) -> str:
    return TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS[key]["en"])


# ==================== Initialize Services ====================

load_dotenv()

# Firestore Database
try:
    db = firestore.Client()
except Exception as e:
    logging.error(f"Failed to initialize Firestore: {e}")
    # Fallback to local emulator if available
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client(project="nutrition-bot-local")


def get_user_ref(user_id: int):
    return db.collection('users').document(str(user_id))


def get_meals_ref(user_id: int):
    return get_user_ref(user_id).collection('meals')


def get_water_ref(user_id: int):
    return get_user_ref(user_id).collection('water')


# Gemini AI
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    nutrition_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    logging.error(f"Failed to initialize Gemini AI: {e}")

# ==================== Bot Setup ====================

bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


# ==================== States ====================

class Registration(StatesGroup):
    language = State()
    name = State()
    age = State()
    height = State()
    weight = State()
    gender = State()
    timezone = State()
    goal = State()


class ReminderStates(StatesGroup):
    setting_water = State()
    setting_meal = State()


class MealLogging(StatesGroup):
    waiting_for_text = State()


# ==================== Keyboard Functions ====================

def get_language_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbek"), KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_gender_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("male", lang)), KeyboardButton(text=t("female", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_timezone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Asia/Tashkent"), KeyboardButton(text="Europe/Moscow")],
            [KeyboardButton(text="Europe/London"), KeyboardButton(text="America/New_York")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_goals_keyboard(lang: str):
    goals_by_lang = {
        "en": ["Skip", "Lose weight", "Gain muscle", "Eat healthier"],
        "ru": ["Пропустить", "Похудеть", "Набрать массу", "Питаться здоровее"],
        "uz": ["O'tkaz", "Vazn yo'qotish", "Massa oshirish", "Sog'lom ovqat"]
    }

    buttons = [KeyboardButton(text=label) for label in goals_by_lang.get(lang, goals_by_lang["en"])]

    return ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_main_menu_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_log_meal", lang)), KeyboardButton(text=t("menu_log_water", lang))],
            [KeyboardButton(text=t("menu_stats", lang)), KeyboardButton(text=t("menu_settings", lang))],
            [KeyboardButton(text=t("menu_help", lang))]
        ],
        resize_keyboard=True
    )


# ==================== Helper Functions ====================

async def get_user_language(user_id: int) -> str:
    """Get user language from Firestore or default to English"""
    try:
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()
        return user_data.get('language', 'en') if user_data else 'en'
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return 'en'


# ==================== Reminder Functions ====================

async def schedule_default_reminders(user_id: int, timezone: str):
    """Schedule default water and meal reminders"""
    try:
        # Water reminders every 2 hours from 8 AM to 10 PM
        for hour in range(8, 22, 2):
            scheduler.add_job(
                send_water_reminder,
                'cron',
                hour=hour,
                timezone=timezone,
                args=[user_id],
                id=f"water_{user_id}_{hour}",
                replace_existing=True
            )

        # Meal reminders
        meal_times = [("09:00", "breakfast"), ("14:51", "lunch"), ("19:00", "dinner")]
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
                replace_existing=True
            )

        logger.info(f"Scheduled reminders for user {user_id}")
    except Exception as e:
        logger.error(f"Error scheduling reminders: {e}")


async def send_water_reminder(user_id: int):
    """Send water reminder to user"""
    try:
        user_lang = await get_user_language(user_id)
        message = t("water_reminder", user_lang)

        # Create inline keyboard for quick water logging
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Log Water", callback_data="log_water")
                ]
            ]
        )

        await bot.send_message(user_id, message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending water reminder: {e}")


async def send_meal_reminder(user_id: int, meal_type: str):
    """Send meal reminder to user"""
    try:
        user_lang = await get_user_language(user_id)
        emoji_map = {"breakfast": "🍳", "lunch": "🍲", "dinner": "🍽"}
        emoji = emoji_map.get(meal_type, "🍔")

        message = f"{emoji} {t('meal_reminder', user_lang)} ({meal_type})"

        # Create inline keyboard for quick meal logging
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📝 Text", callback_data=f"log_meal_text_{meal_type}"),
                    InlineKeyboardButton(text="📷 Photo", callback_data=f"log_meal_photo_{meal_type}")
                ]
            ]
        )

        await bot.send_message(user_id, message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending meal reminder: {e}")


# ==================== Handlers ====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    await message.answer(t("intro", "en"), reply_markup=get_language_keyboard())
    await state.set_state(Registration.language)


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Handle /menu command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("help_text", lang))


@dp.message(Registration.language)
async def reg_language(message: types.Message, state: FSMContext):
    """Handle language selection during registration"""
    text = message.text.lower()
    if "o'zbek" in text or "uzbek" in text or "🇺🇿" in text:
        lang = "uz"
    elif "рус" in text or "rus" in text or "🇷🇺" in text:
        lang = "ru"
    elif "english" in text or "🇬🇧" in text:
        lang = "en"
    else:
        return await message.answer(t("select_language", "en"))

    await state.update_data(language=lang)
    await message.answer(t("ask_name", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.name)


@dp.message(Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
    """Handle name input during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        return await message.answer(t("name_error", lang))
    await state.update_data(name=name)
    await message.answer(t("ask_age", lang))
    await state.set_state(Registration.age)


@dp.message(Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    """Handle age input during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")
    try:
        age = int(message.text.strip())
        if not 0 <= age <= 120:
            return await message.answer(t("age_error", lang))
        await state.update_data(age=age)
        await message.answer(t("ask_height", lang))
        await state.set_state(Registration.height)
    except ValueError:
        await message.answer(t("age_error", lang))


@dp.message(Registration.height)
async def reg_height(message: types.Message, state: FSMContext):
    """Handle height input during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")
    try:
        height = float(message.text.strip())
        if not 50 <= height <= 250:
            return await message.answer(t("height_error", lang))
        await state.update_data(height=height)
        await message.answer(t("ask_weight", lang))
        await state.set_state(Registration.weight)
    except ValueError:
        await message.answer(t("height_error", lang))


@dp.message(Registration.weight)
async def reg_weight(message: types.Message, state: FSMContext):
    """Handle weight input during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")
    try:
        weight = float(message.text.strip())
        if not 20 <= weight <= 300:
            return await message.answer(t("weight_error", lang))
        await state.update_data(weight=weight)
        await message.answer(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))
        await state.set_state(Registration.gender)
    except ValueError:
        await message.answer(t("weight_error", lang))


@dp.message(Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    """Handle gender selection during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")

    gender_map = {
        "en": {"male": ["male"], "female": ["female"]},
        "ru": {"male": ["мужчина", "мужской"], "female": ["женщина", "женский"]},
        "uz": {"male": ["erkak"], "female": ["ayol"]}
    }

    text = message.text.strip().lower()
    gender = None
    for g, terms in gender_map.get(lang, gender_map["en"]).items():
        if any(term.lower() in text.lower() for term in terms):
            gender = g
            break

    if not gender:
        return await message.answer(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))

    await state.update_data(gender=gender)
    await message.answer(t("ask_timezone", lang), reply_markup=get_timezone_keyboard())
    await state.set_state(Registration.timezone)


@dp.message(Registration.timezone)
async def reg_timezone(message: types.Message, state: FSMContext):
    """Handle timezone selection during registration"""
    data = await state.get_data()
    lang = data.get("language", "en")

    try:
        tz = pytz.timezone(message.text.strip())
        await state.update_data(timezone=str(tz))
        await message.answer(t("ask_goal", lang), reply_markup=get_goals_keyboard(lang))
        await state.set_state(Registration.goal)
    except pytz.exceptions.UnknownTimeZoneError:
        await message.answer(t("timezone_error", lang))


@dp.message(Registration.goal)
async def reg_goal(message: types.Message, state: FSMContext):
    """Handle goal selection and complete registration"""
    try:
        data = await state.get_data()
        lang = data.get("language", "en")
        goal = message.text.strip()

        # Skip values in different languages
        skip_values = ["Skip", "Пропустить", "O'tkaz"]
        goal_value = "" if goal in skip_values else goal

        # Save to Firestore
        user_ref = get_user_ref(message.from_user.id)
        user_data = {
            **data,
            'goal': goal_value,
            'registered_at': datetime.now(pytz.utc),
            'telegram_username': message.from_user.username,
            'telegram_id': message.from_user.id,
            'last_active': datetime.now(pytz.utc)
        }

        user_ref.set(user_data)

        # Schedule reminders
        await schedule_default_reminders(message.from_user.id, data['timezone'])

        # Show completion message and main menu
        await message.answer(t("registration_complete", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer("❌ Registration failed. Please try /start again")
        await state.clear()


@dp.message(F.text.lower() == "💧 log water")
@dp.message(F.text.lower() == "💧 записать воду")
@dp.message(F.text.lower() == "💧 suv qayd etish")
@dp.message(Command("water"))
async def log_water(message: types.Message):
    """Handle water logging through command or menu button"""
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        # Log default water amount (250ml)
        get_water_ref(user_id).add({
            'amount': 250,
            'timestamp': datetime.now(pytz.utc)
        })

        await message.answer(t("water_logged", lang))
    except Exception as e:
        logger.error(f"Water logging error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang))


@dp.callback_query(lambda c: c.data == "log_water")
async def callback_log_water(callback_query: types.CallbackQuery):
    """Handle water logging through inline button"""
    try:
        user_id = callback_query.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        # Log default water amount (250ml)
        get_water_ref(user_id).add({
            'amount': 250,
            'timestamp': datetime.now(pytz.utc)
        })

        await callback_query.answer("Water logged successfully!")
        await bot.send_message(user_id, t("water_logged", lang))
    except Exception as e:
        logger.error(f"Water logging error from callback: {e}")
        lang = await get_user_language(callback_query.from_user.id)
        await bot.send_message(callback_query.from_user.id, t("error_processing", lang))


@dp.message(F.text.lower() == "📊 my stats")
@dp.message(F.text.lower() == "📊 моя статистика")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    """Handle stats display through command or menu button and display nutrition statistics"""
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        # Processing message
        await message.answer(t("processing", lang))

        # Get user data
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()

        if not user_data:
            return await message.answer("❌ User data not found. Please register with /start")

        # Water stats - Calculate daily and total water intake
        today = datetime.now(pytz.timezone(user_data.get('timezone', 'UTC'))).date()
        today_start = datetime.combine(today, datetime.min.time(),
                                       tzinfo=pytz.timezone(user_data.get('timezone', 'UTC')))
        today_end = datetime.combine(today, datetime.max.time(), tzinfo=pytz.timezone(user_data.get('timezone', 'UTC')))

        # Convert to UTC for Firestore query
        today_start_utc = today_start.astimezone(pytz.UTC)
        today_end_utc = today_end.astimezone(pytz.UTC)

        # Get water logs
        all_water_docs = list(get_water_ref(user_id).stream())

        # Calculate total water intake
        total_water = sum(doc.to_dict().get('amount', 0) for doc in all_water_docs)

        # Calculate today's water intake
        today_water_docs = list(get_water_ref(user_id)
                                .where('timestamp', '>=', today_start_utc)
                                .where('timestamp', '<=', today_end_utc)
                                .stream())
        today_water = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)

        # Meal stats
        all_meal_docs = list(get_meals_ref(user_id).stream())
        total_meals = len(all_meal_docs)

        # Today's meals
        today_meal_docs = list(get_meals_ref(user_id)
                               .where('timestamp', '>=', today_start_utc)
                               .where('timestamp', '<=', today_end_utc)
                               .stream())
        today_meals = len(today_meal_docs)

        # Calculate recommended water intake based on weight
        weight = user_data.get('weight', 70)
        recommended_water = int(weight * 30)  # 30ml per kg body weight

        # Calculate water percentage of daily goal
        water_percentage = min(int((today_water / recommended_water) * 100), 100) if recommended_water > 0 else 0

        # Create progress bar for water intake
        progress_bar_length = 10
        filled_blocks = int((water_percentage / 100) * progress_bar_length)
        empty_blocks = progress_bar_length - filled_blocks
        progress_bar = "🟦" * filled_blocks + "⬜" * empty_blocks

        # Format response
        response = (
            f"📊 <b>Your Statistics:</b>\n\n"
            f"<b>Today's Summary ({today.strftime('%Y-%m-%d')}):</b>\n"
            f"💧 <b>Water:</b> {today_water}ml / {recommended_water}ml\n"
            f"{progress_bar} {water_percentage}%\n"
            f"🍽 <b>Meals logged today:</b> {today_meals}\n\n"
            f"<b>Total Stats:</b>\n"
            f"💧 <b>Total Water:</b> {total_water}ml\n"
            f"🍽 <b>Total Meals Logged:</b> {total_meals}\n"
        )

        # Add BMI if we have height and weight
        if 'height' in user_data and 'weight' in user_data:
            height_m = user_data['height'] / 100  # convert cm to m
            bmi = user_data['weight'] / (height_m * height_m)
            bmi_category = ""

            if bmi < 18.5:
                bmi_category = "Underweight"
            elif 18.5 <= bmi < 25:
                bmi_category = "Normal weight"
            elif 25 <= bmi < 30:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obesity"

            response += f"\n<b>BMI:</b> {bmi:.1f} ({bmi_category})"

        await message.answer(response, reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Stats error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(F.text.lower() == "❓ help")
@dp.message(F.text.lower() == "❓ помощь")
@dp.message(F.text.lower() == "❓ yordam")
async def show_help(message: types.Message):
    """Show help information"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("help_text", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(F.text.lower() == "⚙️ settings")
@dp.message(F.text.lower() == "⚙️ настройки")
@dp.message(F.text.lower() == "⚙️ sozlamalar")
@dp.message(Command("settings"))
async def show_settings(message: types.Message):
    """Show settings menu"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    settings_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔤 Change Language", callback_data="change_language")],
            [InlineKeyboardButton(text="⏰ Edit Reminders", callback_data="edit_reminders")],
            [InlineKeyboardButton(text="👤 Edit Profile", callback_data="edit_profile")]
        ]
    )

    await message.answer("⚙️ Settings", reply_markup=settings_kb)


@dp.callback_query(lambda c: c.data.startswith("log_meal_text_"))
async def callback_log_meal_text(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle meal logging through text via inline button"""
    meal_type = callback_query.data.split('_')[-1]
    user_id = callback_query.from_user.id
    lang = await get_user_language(user_id)

    await callback_query.answer()
    await state.update_data(meal_type=meal_type)
    await state.set_state(MealLogging.waiting_for_text)
    await bot.send_message(
        user_id,
        f"Please describe what you ate for {meal_type}:",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(MealLogging.waiting_for_text)
async def process_meal_text(message: types.Message, state: FSMContext):
    """Process meal text input after callback"""
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)
        data = await state.get_data()
        meal_type = data.get('meal_type', 'meal')
        text = message.text.strip()

        # Wait message
        await message.answer(t("processing", lang))

        # Analyze with Gemini
        try:
            response = nutrition_model.generate_content(
                f"Provide nutritional info for {text} in format: 1) Calories 2) Protein 3) Carbs 4) Fat. Use emojis and short bullets."
            )
            analysis = response.text
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            analysis = "Failed to analyze. Please try again."

        # Store in Firestore
        get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'text_input': text,
            'meal_type': meal_type
        })

        await message.answer(f"📝 <b>{meal_type.capitalize()} logged:</b>\n\n{analysis}",
                             reply_markup=get_main_menu_keyboard(lang))
        await state.clear()
    except Exception as e:
        logger.error(f"Text input error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()


@dp.callback_query(lambda c: c.data.startswith("log_meal_photo_"))
async def callback_log_meal_photo(callback_query: types.CallbackQuery):
    """Handle meal logging through photo via inline button"""
    meal_type = callback_query.data.split('_')[-1]
    user_id = callback_query.from_user.id
    lang = await get_user_language(user_id)

    await callback_query.answer()
    await bot.send_message(
        user_id,
        f"Please send a photo of your {meal_type}.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(F.text.lower() == "🍽 log meal")
@dp.message(F.text.lower() == "🍽 записать прием пищи")
@dp.message(F.text.lower() == "🍽 ovqat qayd etish")
@dp.message(Command("log_meal"))
async def log_meal_command(message: types.Message):
    """Handle meal logging from menu button"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    meal_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🍳 Breakfast", callback_data="log_meal_text_breakfast"),
                InlineKeyboardButton(text="🥪 Lunch", callback_data="log_meal_text_lunch")
            ],
            [
                InlineKeyboardButton(text="🍽 Dinner", callback_data="log_meal_text_dinner"),
                InlineKeyboardButton(text="🍫 Snack", callback_data="log_meal_text_snack")
            ]
        ]
    )

    await message.answer("Select meal type:", reply_markup=meal_kb)


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    """Handle food photo submission"""
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        # Processing message
        processing_msg = await message.answer(t("processing", lang))

        # Download photo
        photo = message.photo[-1]  # Get the highest resolution photo
        file_info = await bot.get_file(photo.file_id)
        file_content = await bot.download_file(file_info.file_path)

        # Read file content as bytes
        img_bytes = file_content.read()

        # Analyze with Gemini
        try:
            response = vision_model.generate_content([
                "Analyze this food and provide: 1) Food name 2) Calories 3) Protein 4) Carbs 5) Fat. Use emojis and concise format.",
                {"mime_type": "image/jpeg", "data": img_bytes}
            ])
            analysis = response.text
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            analysis = "Failed to analyze image. Please try again or describe your meal in text."

        # Store in Firestore
        get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'photo_id': photo.file_id
        })

        # Delete processing message and send result
        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(f"📸 <b>Food Analysis:</b>\n\n{analysis}", reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Photo processing error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(F.document)
async def handle_document(message: types.Message):
    """Handle image documents"""
    try:
        # Check if document is an image
        if not message.document.mime_type.startswith('image/'):
            return

        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        # Processing message
        processing_msg = await message.answer(t("processing", lang))

        # Download document
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_content = await bot.download_file(file_info.file_path)

        # Read file content as bytes
        img_bytes = file_content.read()

        # Analyze with Gemini
        try:
            response = vision_model.generate_content([
                "Analyze this food and provide: 1) Food name 2) Calories 3) Protein 4) Carbs 5) Fat. Use emojis and concise format.",
                {"mime_type": message.document.mime_type, "data": img_bytes}
            ])
            analysis = response.text
        except Exception as e:
            logger.error(f"Vision API error with document: {e}")
            analysis = "Failed to analyze image. Please try again or describe your meal in text."

        # Store in Firestore
        get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'document_id': file_id
        })

        # Delete processing message and send result
        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(f"📸 <b>Food Analysis:</b>\n\n{analysis}", reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(
    lambda msg: msg.text and not msg.text.startswith('/') and not any(keyword in msg.text.lower() for keyword in [
        "log water", "записать воду", "suv qayd etish",
        "my stats", "моя статистика", "mening statistikam",
        "settings", "настройки", "sozlamalar",
        "log meal", "записать прием пищи", "ovqat qayd etish",
        "help", "помощь", "yordam"
    ]))
async def handle_text(message: types.Message, state: FSMContext):
    """Handle food text descriptions"""
    # Skip if we're in a state
    current_state = await state.get_state()
    if current_state is not None and current_state == MealLogging.waiting_for_text:
        return

    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Update user's last active timestamp
        get_user_ref(user_id).update({
            'last_active': datetime.now(pytz.utc)
        })

        text = message.text.strip()

        # Processing message
        processing_msg = await message.answer(t("processing", lang))

        # Analyze with Gemini
        try:
            response = nutrition_model.generate_content(
                f"Provide nutritional info for {text} in format: 1) Calories 2) Protein 3) Carbs 4) Fat. Use emojis and short bullets."
            )
            analysis = response.text
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            analysis = "Failed to analyze. Please try again."

        # Store in Firestore
        get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'text_input': text
        })

        # Delete processing message and send result
        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(f"📝 <b>Food Analysis:</b>\n\n{analysis}", reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


# ==================== Main ====================

async def main():
    # Initialize scheduler
    scheduler.start()

    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Proper shutdown
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )
    asyncio.run(main())