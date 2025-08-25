import os
import asyncio
import logging
from datetime import datetime, timedelta, date as DateObject
import pytz
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple, List
import re
import io

from telegram import (
    Bot, Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext,
    ConversationHandler, CallbackQueryHandler, PicklePersistence
)
from telegram.constants import ParseMode, ChatAction

from google.cloud import firestore
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from googletrans import Translator

# ==================== Project Directory Setup ====================
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_DIR = os.path.join(PROJECT_DIR, "credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
logger.info(f"Project directory: {PROJECT_DIR}")

# ==================== Load Environment Variables ====================
logger.info("Loading environment variables from .env file...")
if load_dotenv():
    logger.info(".env file loaded successfully.")
else:
    logger.warning(".env file not found or failed to load. Relying on system environment variables.")

# ==================== Logging Setup ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)
logger.info("Logging configured.")

# ==================== Translation Service ====================
translator_service = None
logger.info("Initializing Translator service...")
try:
    translator_service = Translator()
    logger.info("Translator service initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Translator service: {e}", exc_info=True)


def translate(text: str, target_lang: str) -> str:
    if not translator_service:
        return text
    if not text or not isinstance(text, str) or not text.strip():
        return text
    if target_lang == 'en':
        return text
    try:
        if text.startswith("__") and text.endswith("__") or text == "N/A":
            return text
        translation = translator_service.translate(text, dest=target_lang)
        return translation.text
    except Exception as e:
        logger.warning(f"Translation error for text '{text}' to '{target_lang}': {e}")
        return text


# ==================== Translations Dictionary ====================
TRANSLATIONS = {
    "intro": {
        "en": "👋 Hello! I am NutritionBot. Please select your language:",
        "ru": "👋 Привет! Я NutritionBot. Пожалуйста, выберите язык:",
        "uz": "👋 Salom! Men NutritionBot. Tilni tanlang:"
    },
    "select_language": {
        "en": "Choose your language:", "ru": "Выберите ваш язык:", "uz": "Tilni tanlang:"
    },
    "language_selected_message": {
        "en": "Language set to English. Let's get started!",
        "ru": "Язык установлен на Русский. Давайте начнем!",
        "uz": "Til O'zbek tiliga o'rnatildi. Boshlaymiz!"
    },
    "ask_name": {"en": "Enter your name:", "ru": "Введите ваше имя:", "uz": "Ismingizni kiriting:"},
    "name_error": {"en": "Name should be 2-50 characters.", "ru": "Имя должно быть от 2 до 50 символов.",
                   "uz": "Ism 2 dan 50 belgigacha bo'lishi kerak."},
    "ask_age": {"en": "Enter your age:", "ru": "Введите ваш возраст:", "uz": "Yoshingizni kiriting:"},
    "age_error": {"en": "Please enter a valid age (0-120).", "ru": "Введите правильный возраст (0-120).",
                  "uz": "Iltimos, 0 dan 120 gacha yoshingizni kiriting."},
    "ask_height": {"en": "Enter your height (cm):", "ru": "Введите ваш рост (см):", "uz": "Bo'yingizni kiriting (sm):"},
    "height_error": {"en": "Valid height: 50-250 cm.", "ru": "Правильный рост: 50-250 см.",
                     "uz": "Iltimos, 50 dan 250 sm gacha bo'yingizni kiriting."},
    "ask_weight": {"en": "Enter your weight (kg):", "ru": "Введите ваш вес (кг):", "uz": "Vazningizni kiriting (kg):"},
    "weight_error": {"en": "Valid weight: 20-300 kg.", "ru": "Правильный вес: 20-300 кг.",
                     "uz": "Iltimos, 20 dan 300 kg gacha vazningizni kiriting."},
    "ask_gender": {"en": "Select your gender:", "ru": "Выберите ваш пол:", "uz": "Jinsingizni tanlang:"},
    "ask_timezone": {"en": "Select or enter your timezone:", "ru": "Выберите или введите ваш часовой пояс:",
                     "uz": "Vaqt mintaqangizni tanlang yoki kiriting:"},
    "timezone_error": {"en": "Invalid timezone. Select or enter valid one.",
                       "ru": "Неверный часовой пояс. Выберите или введите правильный.",
                       "uz": "Noto'g'ri vaqt mintaqasi. Tanlang yoki to'g'risini kiriting."},
    "ask_goal_text": {"en": "What's your primary health goal? Select one or type your own:",
                      "ru": "Какова ваша основная цель? Выберите или введите свою:",
                      "uz": "Asosiy sog'liq maqsadingiz nima? Tanlang yoki o'zingiznikini yozing:"},
    "goal_lose_weight": {"en": "Lose Weight", "ru": "Похудеть", "uz": "Vazn yo'qotish"},
    "goal_gain_muscle": {"en": "Gain Muscle", "ru": "Набрать Мышцы", "uz": "Mushaklarni Kuchaytirish"},
    "goal_eat_healthier": {"en": "Eat Healthier", "ru": "Питаться Здоровее", "uz": "Sog'lomroq Ovqatlanish"},
    "goal_look_beautiful": {"en": "Look Beautiful/Fit", "ru": "Выглядеть Красиво/Подтянуто",
                            "uz": "Go'zal/Sportiv Ko'rinish"},
    "skip_goal": {"en": "Skip", "ru": "Пропустить", "uz": "O'tkazib yuborish"},
    "ask_calorie_goal": {
        "en": "What is your daily calorie goal? (e.g., 2000 kcal). We can estimate this later if you skip.",
        "ru": "Какова ваша дневная цель по калориям? (например, 2000 ккал). Мы можем оценить это позже, если пропустите.",
        "uz": "Kunlik kaloriya maqsadingiz nima? (masalan, 2000 kkal). Keyinroq taxmin qilishimiz mumkin."},
    "calorie_goal_error": {"en": "Please enter a valid number for calorie goal (e.g., 1800) or type 'skip'.",
                           "ru": "Введите число для цели по калориям (например, 1800) или 'пропустить'.",
                           "uz": "Kaloriya maqsadi uchun raqam kiriting (masalan, 1800) yoki 'skip' yozing."},
    "ask_dream_weight": {"en": "What's your dream weight (kg)? (Optional, type 'skip' to omit)",
                         "ru": "Какой ваш желаемый вес (кг)? (Необязательно, введите 'пропустить', чтобы пропустить)",
                         "uz": "Orzuyingizdagi vazn qancha (kg)? (Ixtiyoriy, o'tkazib yuborish uchun 'skip' deb yozing)"},
    "dream_weight_error": {"en": "Please enter a valid weight (e.g., 65.5) or 'skip'.",
                           "ru": "Пожалуйста, введите действительный вес (например, 65.5) или 'пропустить'.",
                           "uz": "Iltimos, haqiqiy vaznni (masalan, 65.5) yoki 'skip' deb yozing."},
    "registration_complete": {"en": "✅ Registration complete! Send food info (text or photo). Use /menu.",
                              "ru": "✅ Регистрация завершена! Отправьте инфо/фото еды. Используйте /menu.",
                              "uz": "✅ Ro'yxatdan o'tish yakunlandi! Ovqat info/rasmlarini yuboring. /menu dan foydalaning."},
    "water_reminder": {"en": "💧 Time to drink water! Stay hydrated!",
                       "ru": "💧 Время пить воду! Поддерживайте водный баланс!",
                       "uz": "💧 Suv ichish vaqti! Suv miqdorini saqlang!"},
    "meal_reminder": {"en": "⏰ Don't forget to log your {meal_type}!", "ru": "⏰ Не забудьте записать свой {meal_type}!",
                      "uz": "⏰ {meal_type} qayd etishni unutmang!"},
    "water_logged": {"en": "✅ Water intake recorded! +250ml", "ru": "✅ Прием воды зарегистрирован! +250мл",
                     "uz": "✅ Suv miqdori qayd etildi! +250ml"},
    "processing": {"en": "⏳ Processing your request...", "ru": "⏳ Обрабатываю ваш запрос...",
                   "uz": "⏳ So'rovingiz bajarilmoqda..."},
    "error_processing": {"en": "❌ Error processing. Please try again.", "ru": "❌ Ошибка обработки. Попробуйте снова.",
                         "uz": "❌ Qayta ishlashda xatolik. Qaytadan urinib ko'ring."},
    "main_menu": {"en": "📋 Main Menu - What would you like to do?", "ru": "📋 Главное меню - Что бы вы хотели сделать?",
                  "uz": "📋 Asosiy menyu - Nima qilmoqchisiz?"},
    "menu_log_meal": {"en": "🍽 Log Meal", "ru": "🍽 Записать прием пищи", "uz": "🍽 Ovqat qayd etish"},
    "menu_log_water": {"en": "💧 Log Water", "ru": "💧 Записать воду", "uz": "💧 Suv qayd etish"},
    "menu_stats": {"en": "📊 My Stats/Goals", "ru": "📊 Моя статистика/Цели", "uz": "📊 Mening statistikam/Maqsadlarim"},
    "menu_settings": {"en": "⚙️ Settings", "ru": "⚙️ Настройки", "uz": "⚙️ Sozlamalar"},
    "menu_help": {"en": "❓ Help", "ru": "❓ Помощь", "uz": "❓ Yordam"},
    "help_text": {
        "en": "🌟 <b>How to Use NutritionBot:</b>\n\n"
              "• <b>Log Meals:</b> Send a photo of your food or text describing what you ate (e.g., after using /logmeal or from a reminder).\n"
              "• <b>Log Water:</b> Use the '💧 Log Water' button or /water command.\n"
              "• <b>View Stats/Goals:</b> Use the '📊 My Stats/Goals' button or /stats command to see your progress.\n"
              "• <b>Settings:</b> Use '⚙️ Settings' or /settings for language, profile, reminders.\n"
              "• <b>Main Menu:</b> Use /menu command anytime.\n\n"
              "For feedback, questions, or problems, contact @jurat1.",
        "ru": "🌟 <b>Как использовать NutritionBot:</b>\n\n"
              "• <b>Запись питания:</b> Отправьте фото еды или текст с описанием (например, после /logmeal или из напоминания).\n"
              "• <b>Запись воды:</b> Используйте кнопку '💧 Записать воду' или команду /water.\n"
              "• <b>Просмотр статистики/целей:</b> Используйте кнопку '📊 Моя статистика/Цели' или команду /stats.\n"
              "• <b>Настройки:</b> Используйте '⚙️ Настройки' или /settings для языка, профиля, напоминаний.\n"
              "• <b>Главное меню:</b> Используйте команду /menu в любой момент.\n\n"
              "Для обратной связи, вопросов или проблем, пишите @jurat1.",
        "uz": "🌟 <b>NutritionBot-dan qanday foydalanish mumkin:</b>\n\n"
              "• <b>Ovqatni qayd etish:</b> Ovqatning rasmini yoki tavsifini yuboring (masalan, /logmeal dan keyin yoki eslatmadan).\n"
              "• <b>Suvni qayd etish:</b> '💧 Suv qayd etish' tugmasini yoki /water buyrug'ini ishlating.\n"
              "• <b>Statistika/Maqsadlar:</b> '📊 Mening statistikam/Maqsadlarim' tugmasini yoki /stats buyrug'ini ishlating.\n"
              "• <b>Sozlamalar:</b> Til, profil, eslatmalar uchun '⚙️ Sozlamalar' yoki /settings dan foydalaning.\n"
              "• <b>Asosiy menyu:</b> Istalgan vaqtda /menu buyrug'ini ishlating.\n\n"
              "Fikr-mulohaza, savollar yoki muammolar uchun @jurat1 ga murojaat qiling."
    },
    "male": {"en": "Male", "ru": "Мужской", "uz": "Erkak"},
    "female": {"en": "Female", "ru": "Женский", "uz": "Ayol"},
    "settings_title": {"en": "⚙️ Settings", "ru": "⚙️ Настройки", "uz": "⚙️ Sozlamalar"},
    "change_language": {"en": "🔤 Change Language", "ru": "🔤 Изменить язык", "uz": "🔤 Tilni o'zgartirish"},
    "edit_reminders": {"en": "⏰ Edit Reminders", "ru": "⏰ Редактировать напоминания",
                       "uz": "⏰ Eslatmalarni tahrirlash"},
    "edit_profile": {"en": "👤 Edit Profile", "ru": "👤 Редактировать профиль", "uz": "👤 Profilni tahrirlash"},
    "back_to_menu": {"en": "🔙 Back to Menu", "ru": "🔙 Назад в меню", "uz": "🔙 Menyuga qaytish"},
    "back_to_settings": {"en": "⚙️ Back to Settings", "ru": "⚙️ Назад в настройки", "uz": "⚙️ Sozlamalarga qaytish"},
    "back_to_profile_fields": {"en": "👤 Back to Profile Fields", "ru": "👤 Назад к полям профиля",
                               "uz": "👤 Profil maydonlariga qaytish"},
    "select_new_language": {"en": "Select your new language:", "ru": "Выберите новый язык:",
                            "uz": "Yangi tilni tanlang:"},
    "language_changed": {"en": "✅ Language changed successfully!", "ru": "✅ Язык успешно изменен!",
                         "uz": "✅ Til muvaffaqiyatli o'zgartirildi!"},
    "edit_which_field": {"en": "Select field to edit:", "ru": "Выберите поле для редактирования:",
                         "uz": "Tahrirlash uchun maydonni tanlang:"},
    "edit_name": {"en": "✏️ Name", "ru": "✏️ Имя", "uz": "✏️ Ism"},
    "edit_age": {"en": "✏️ Age", "ru": "✏️ Возраст", "uz": "✏️ Yosh"},
    "edit_height": {"en": "✏️ Height", "ru": "✏️ Рост", "uz": "✏️ Bo'y"},
    "edit_weight": {"en": "✏️ Weight", "ru": "✏️ Вес", "uz": "✏️ Vazn"},
    "edit_goal_text": {"en": "✏️ Primary Goal", "ru": "✏️ Основная цель", "uz": "✏️ Asosiy Maqsad"},
    "edit_calorie_goal": {"en": "✏️ Calorie Goal", "ru": "✏️ Цель калорий", "uz": "✏️ Kaloriya maqsadi"},
    "field_name_daily_calorie_goal": {"en": "Daily Calorie Goal", "ru": "Дневная цель калорий",
                                      "uz": "Kunlik Kaloriya Maqsadi"},
    "edit_dream_weight": {"en": "✏️ Dream Weight", "ru": "✏️ Желаемый вес", "uz": "✏️ Orzudagi Vazn"},
    "reminder_settings_text": {
        "en": "⏰ Reminder Settings\n\nWater reminders: {water_status}\nMeal reminders: {meal_status}",
        "ru": "⏰ Настройки напоминаний\n\nНапоминания о воде: {water_status}\nНапоминания о еде: {meal_status}",
        "uz": "⏰ Eslatma sozlamalari\n\nSuv eslatmalari: {water_status}\nOvqat eslatmalari: {meal_status}"},
    "toggle_water_reminders": {"en": "💧 Water Reminders", "ru": "💧 Напоминания о воде", "uz": "💧 Suv eslatmalari"},
    "toggle_meal_reminders": {"en": "🍽 Meal Reminders", "ru": "🍽 Напоминания о еде", "uz": "🍽 Ovqat eslatmalari"},
    "reminder_on_off_template": {"en": " ({status})", "ru": " ({status})", "uz": " ({status})"},
    "on_status": {"en": "ON", "ru": "ВКЛ", "uz": "YONIQ"},
    "off_status": {"en": "OFF", "ru": "ВЫКЛ", "uz": "O'CHIQ"},
    "reminder_toggled_alert": {"en": "{action} reminders: {status}", "ru": "Напоминания {action}: {status}",
                               "uz": "{action} eslatmalari: {status}"},
    "enter_new_value": {"en": "Enter new value for {field}:", "ru": "Введите новое значение для {field}:",
                        "uz": "{field} uchun yangi qiymatni kiriting:"},
    "current_value_is": {"en": "Current", "ru": "Текущее", "uz": "Joriy"},
    "profile_updated": {"en": "✅ Profile updated successfully!", "ru": "✅ Профиль успешно обновлен!",
                        "uz": "✅ Profil muvaffaqiyatli yangilandi!"},
    "ask_log_meal_general": {"en": "Please send a description or photo of your {meal_type}:",
                             "ru": "Опишите или пришлите фото вашего {meal_type}:",
                             "uz": "{meal_type} uchun tavsif yoki rasm yuboring:"},
    "log_meal_type_select": {"en": "Which meal are you logging?", "ru": "Какой прием пищи вы записываете?",
                             "uz": "Qaysi ovqatni qayd etyapsiz?"},
    "food_analysis_header": {"en": "📊 <b>Food Analysis for {food_name}:</b>\n\n",
                             "ru": "📊 <b>Анализ еды для {food_name}:</b>\n\n",
                             "uz": "📊 <b>{food_name} uchun ovqat tahlili:</b>\n\n"},
    "food_boast_text": {"en": "💡 <b>Nutritional Insights:</b>", "ru": "💡 <b>Пищевая ценность:</b>",
                        "uz": "💡 <b>Ozuqaviy tushunchalar:</b>"},
    "positive_side_label": {"en": "Positive", "ru": "Положительное", "uz": "Ijobiy"},
    "negative_side_label": {"en": "Caution", "ru": "Осторожно", "uz": "Ehtiyot bo'ling"},
    "stats_your_stats_and_goals": {"en": "📊 <b>Your Statistics & Goals:</b>", "ru": "📊 <b>Ваша статистика и цели:</b>",
                                   "uz": "📊 <b>Sizning statistika va maqsadingiz:</b>"},
    "stats_daily_calorie_goal": {"en": "🎯 Daily Calorie Goal", "ru": "🎯 Дневная цель калорий",
                                 "uz": "🎯 Kunlik Kaloriya Maqsadi"},
    "stats_calories_remaining": {"en": "🔥 Calories Remaining", "ru": "🔥 Осталось калорий",
                                 "uz": "🔥 Qolgan kaloriyalar"},
    "stats_calories_consumed": {"en": "Consumed", "ru": "Потреблено", "uz": "Iste'mol qilingan"},
    "stats_today_summary": {"en": "<b>Today's Summary ({}):</b>", "ru": "<b>Сводка за сегодня ({}):</b>",
                            "uz": "<b>Bugungi kun xulosasi ({}):</b>"},
    "stats_water": {"en": "Water", "ru": "Вода", "uz": "Suv"},
    "stats_calories": {"en": "Calories", "ru": "Калории", "uz": "Kaloriyalar"},
    "stats_meals_today": {"en": "Meals logged today", "ru": "Приемов пищи сегодня",
                          "uz": "Bugun qayd etilgan ovqatlar"},
    "stats_total_stats": {"en": "<b>Total Stats (since registration):</b>",
                          "ru": "<b>Общая статистика (с момента регистрации):</b>",
                          "uz": "<b>Umumiy statistika (ro'yxatdan o'tgandan beri):</b>"},
    "stats_total_water": {"en": "Total Water", "ru": "Всего воды", "uz": "Jami suv"},
    "stats_total_meals_logged": {"en": "Total Meals Logged", "ru": "Всего приемов пищи",
                                 "uz": "Jami qayd etilgan ovqatlar"},
    "stats_bmi": {"en": "BMI", "ru": "ИМТ", "uz": "TVI"},
    "underweight": {"en": "Underweight", "ru": "Недостаточный вес", "uz": "Kam vazn"},
    "normal_weight": {"en": "Normal weight", "ru": "Нормальный вес", "uz": "Normal vazn"},
    "overweight": {"en": "Overweight", "ru": "Избыточный вес", "uz": "Ortiqcha vazn"},
    "obesity": {"en": "Obesity", "ru": "Ожирение", "uz": "Semizlik"},
    "user_data_not_found": {"en": "❌ User data not found. Please register with /start",
                            "ru": "❌ Данные пользователя не найдены. Зарегистрируйтесь с /start",
                            "uz": "❌ Foydalanuvchi ma'lumotlari topilmadi. /start orqali ro'yxatdan o'ting"},
    "not_registered": {"en": "You are not registered. Please use /start to begin.",
                       "ru": "Вы не зарегистрированы. Пожалуйста, используйте /start, чтобы начать.",
                       "uz": "Siz roʻyxatdan oʻtmagansiz. Boshlash uchun /start buyrugʻidan foydalaning."},
    "breakfast": {"en": "🍳 Breakfast", "ru": "🍳 Завтрак", "uz": "🍳 Nonushta"},
    "lunch": {"en": "🥪 Lunch", "ru": "🥪 Обед", "uz": "🥪 Tushlik"},
    "dinner": {"en": "🍽 Dinner", "ru": "🍽 Ужин", "uz": "🍽 Kechki ovqat"},
    "snack": {"en": "🍫 Snack", "ru": "🍫 Перекус", "uz": "🍫 Yengil tamaddi"},
    "general_meal": {"en": "Meal", "ru": "Прием пищи", "uz": "Ovqat"},
    "goal_not_set_in_stats": {"en": "Daily calorie goal not set. Set it in /settings -> Edit Profile to see progress.",
                              "ru": "Дневная цель по калориям не установлена. Установите её в /settings -> Редактировать профиль для отслеживания.",
                              "uz": "Kunlik kaloriya maqsadi o'rnatilmagan. Uni /settings -> Profilni tahrirlash bo'limida o'rnating."},
    "no_calories_logged_today_in_stats": {"en": "No calories logged today.", "ru": "Сегодня калории не были записаны.",
                                          "uz": "Bugun kaloriyalar qayd etilmadi."},
    "field_name_name": {"en": "Name", "ru": "Имя", "uz": "Ism"},
    "field_name_age": {"en": "Age", "ru": "Возраст", "uz": "Yosh"},
    "field_name_height": {"en": "Height", "ru": "Рост", "uz": "Bo'y"},
    "field_name_weight": {"en": "Weight", "ru": "Вес", "uz": "Vazn"},
    "field_name_goal_text": {"en": "Primary Goal", "ru": "Основная цель", "uz": "Asosiy Maqsad"},
    "field_name_dream_weight": {"en": "Dream Weight", "ru": "Желаемый вес", "uz": "Orzudagi Vazn"},
    "protein": {"en": "Protein", "ru": "Белки", "uz": "Oqsil"},
    "carbohydrates": {"en": "Carbohydrates", "ru": "Углеводы", "uz": "Uglevodlar"},
    "fat": {"en": "Fat", "ru": "Жиры", "uz": "Yog'lar"},
    "micronutrients": {"en": "Micronutrients", "ru": "Микронутриенты", "uz": "Mikronutrientlar"},
    "not_available": {"en": "N/A", "ru": "Н/Д", "uz": "Mavjud emas"},
    "cancel_registration": {"en": "Cancel Registration", "ru": "Отменить регистрацию",
                            "uz": "Ro'yxatdan o'tishni bekor qilish"},
    "registration_cancelled": {"en": "Registration cancelled.", "ru": "Регистрация отменена.",
                               "uz": "Ro'yxatdan o'tish bekor qilindi."},
    "action_cancelled": {"en": "Action cancelled.", "ru": "Действие отменено.", "uz": "Amal bekor qilindi."},
    "cancel_button_text": {"en": "❌ Cancel", "ru": "❌ Отмена", "uz": "❌ Bekor qilish"},
    "daily_motivation_template": {
        "en": "🌟 Daily Motivation for {name}!\n{message}",
        "ru": "🌟 Ежедневная мотивация для {name}!\n{message}",
        "uz": "🌟 {name} uchun kunlik motivatsiya!\n{message}"
    },
}
logger.info("TRANSLATIONS dictionary loaded.")


def t(key: str, lang: str, **kwargs) -> str:
    translation = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", f"__{key}__"))
    if kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing placeholder in translation for key '{key}', lang '{lang}': {e}")
            return translation
        except Exception as e_fmt:
            logger.warning(f"Formatting error for translation key '{key}', lang '{lang}': {e_fmt}")
            return translation
    return translation


# ==================== Firestore Database ====================
db: Optional[firestore.Client] = None
logger.info("Initializing Firestore...")
try:
    db = firestore.Client()
    logger.info("Firestore initialized successfully (Live or using GOOGLE_APPLICATION_CREDENTIALS).")
except Exception as e:
    logger.error(f"Failed to initialize Firestore with default credentials: {e}", exc_info=True)
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        logger.info(
            f"FIRESTORE_EMULATOR_HOST is set to '{os.getenv('FIRESTORE_EMULATOR_HOST')}', attempting to connect to emulator.")
        try:
            db = firestore.Client()
            logger.info("Firestore initialized with existing emulator settings (or inferred project ID).")
        except Exception as e_emu_existing:
            logger.error(f"Failed with existing emulator settings: {e_emu_existing}", exc_info=True)
            logger.info("Attempting to initialize Firestore with emulator and default project 'nutrition-bot-local'...")
            try:
                db = firestore.Client(project="nutrition-bot-local")
                logger.info("Firestore initialized with emulator at localhost:8080 (project 'nutrition-bot-local').")
            except Exception as e_emu_default:
                logger.critical(
                    f"Failed to initialize Firestore with emulator (default project): {e_emu_default}. Firestore features will be unavailable.",
                    exc_info=True)
    else:
        logger.warning(
            "FIRESTORE_EMULATOR_HOST not set. Firestore default credentials failed. Firestore features will be unavailable if not using GOOGLE_APPLICATION_CREDENTIALS.")

if db is None:
    logger.critical(
        "CRITICAL: Firestore (db) is None after initialization attempts. Bot functionality will be severely limited.")


def get_user_ref(user_id: int) -> Optional[firestore.DocumentReference]:
    if not db: return None
    return db.collection('users').document(str(user_id))


def get_meals_ref(user_id: int) -> Optional[firestore.CollectionReference]:
    user_ref = get_user_ref(user_id)
    if not user_ref: return None
    return user_ref.collection('meals')


def get_water_ref(user_id: int) -> Optional[firestore.CollectionReference]:
    user_ref = get_user_ref(user_id)
    if not user_ref: return None
    return user_ref.collection('water')


# ==================== Gemini AI ====================
nutrition_model: Optional[genai.GenerativeModel] = None
vision_model: Optional[genai.GenerativeModel] = None
logger.info("Initializing Gemini AI models...")
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not found in environment variables. AI features will be disabled.")
    else:
        logger.info("GEMINI_API_KEY found. Configuring GenAI...")
        genai.configure(api_key=gemini_api_key)
        logger.info("GenAI configured. Initializing models...")
        nutrition_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        logger.info("Gemini AI models (gemini-1.5-flash-latest) initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}. AI features will be disabled.", exc_info=True)

if nutrition_model is None or vision_model is None:
    logger.warning("One or both Gemini AI models are None. AI features will be disabled or limited.")

# ==================== Bot Setup ====================
logger.info("Retrieving BOT_TOKEN...")
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("CRITICAL: BOT_TOKEN not found in environment variables. The bot cannot start. Exiting.")
    exit(1)
logger.info("BOT_TOKEN found.")

scheduler: Optional[AsyncIOScheduler] = None
logger.info("APScheduler placeholder defined globally.")


# ==================== Helper Functions ====================
async def get_user_language_db(user_id: int, context: Optional[CallbackContext] = None) -> str:
    if context and 'language' in context.user_data:
        return context.user_data['language']
    user_ref = get_user_ref(user_id)
    if user_ref:
        try:
            user_doc = await asyncio.to_thread(user_ref.get)
            if user_doc.exists:
                lang = user_doc.to_dict().get('language', 'en')
                if context: context.user_data['language'] = lang
                return lang
        except Exception as e:
            logger.error(f"Error fetching language for user {user_id} from DB: {e}")
    return 'en'


def estimate_daily_calories(weight_kg: Optional[float], height_cm: Optional[float], age: Optional[int],
                            gender: Optional[str], goal: Optional[str],
                            dream_weight_kg: Optional[float]) -> Optional[int]:
    if not all([isinstance(weight_kg, (int, float)),
                isinstance(height_cm, (int, float)),
                isinstance(age, int),
                isinstance(gender, str)]):
        logger.warning(
            f"Missing or invalid type for BMR calculation: w={weight_kg}, h={height_cm}, a={age}, g={gender}")
        return None
    weight_kg = float(weight_kg)
    height_cm = float(height_cm)
    age = int(age)
    if gender.lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    elif gender.lower() == "female":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        return None
    tdee = bmr * 1.375
    calorie_goal = tdee
    if goal and isinstance(goal, str):
        if "lose" in goal.lower():
            calorie_goal -= 500
        elif "gain" in goal.lower() and "muscle" in goal.lower():
            calorie_goal += 300
    return int(max(1200, calorie_goal))


def get_day_utc_boundaries(local_date: DateObject, user_timezone: pytz.tzinfo) -> Tuple[datetime, datetime]:
    start_local = datetime.combine(local_date, datetime.min.time(), tzinfo=user_timezone)
    end_local = start_local + timedelta(days=1) - timedelta(microseconds=1)
    start_utc = start_local.astimezone(pytz.utc)
    end_utc = end_local.astimezone(pytz.utc)
    return start_utc, end_utc


async def process_food_input(food_description: str, photo_bytes: Optional[bytes], lang: str) -> Dict[str, Any]:
    if not nutrition_model:
        logger.error("Nutrition model not available.")
        return {
            "food_name": "Unknown",
            "calories_estimated": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "micronutrients": [],
            "positive_points": ["Unable to analyze due to missing AI model."],
            "negative_points": []
        }
    try:
        prompt = f"""
        Analyze the following food item based on the description or image provided.
        Description: {food_description or "No description provided."}
        Provide a detailed nutritional analysis in the following JSON format:
        {
        "food_name": "Name of the food item",
            "calories_estimated": Integer (kcal per typical serving),
            "protein_g": Float (grams per serving),
            "carbs_g": Float (grams per serving),
            "fat_g": Float (grams per serving),
            "micronutrients": ["List of key vitamins/minerals, if known"],
            "positive_points": ["List of health benefits or positive nutritional aspects"],
            "negative_points": ["List of potential health concerns or negative aspects"]
        }
        Ensure all numeric values are realistic and based on standard serving sizes. If no description is provided and only an image is available, describe what you infer from the image. If data is uncertain, use reasonable estimates and note in positive/negative points.
        """
        if photo_bytes:
            logger.info("Processing food input with photo.")
            image_stream = io.BytesIO(photo_bytes)
            response = await asyncio.to_thread(nutrition_model.generate_content,
                                               [prompt, {"mime_type": "image/jpeg", "data": image_stream.getvalue()}])
        else:
            logger.info("Processing food input with text description.")
            response = await asyncio.to_thread(nutrition_model.generate_content, prompt)

        response_text = response.text.strip()
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        import json
        analysis = json.loads(response_text)

        required_keys = ["food_name", "calories_estimated", "protein_g", "carbs_g", "fat_g", "micronutrients",
                         "positive_points", "negative_points"]
        for key in required_keys:
            if key not in analysis:
                logger.warning(f"Missing key '{key}' in AI response: {response_text}")
                analysis[key] = 0 if key in ["calories_estimated", "protein_g", "carbs_g", "fat_g"] else [] if key in [
                    "micronutrients", "positive_points", "negative_points"] else "Unknown"

        return analysis
    except Exception as e:
        logger.error(f"Error processing food input: {e}", exc_info=True)
        return {
            "food_name": "Unknown",
            "calories_estimated": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "micronutrients": [],
            "positive_points": ["Unable to analyze due to processing error."],
            "negative_points": []
        }


# ==================== Keyboard Functions ====================
def get_language_keyboard_reg():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🇺🇿 O'zbek"), KeyboardButton(text="🇷🇺 Русский")],
                                         [KeyboardButton(text="🇬🇧 English")]], resize_keyboard=True,
                               one_time_keyboard=True)


def get_gender_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("male", lang)), KeyboardButton(text=t("female", lang))]], resize_keyboard=True,
        one_time_keyboard=True)


def get_timezone_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Asia/Tashkent"), KeyboardButton(text="Europe/Moscow")],
                                         [KeyboardButton(text="Europe/London"),
                                          KeyboardButton(text="America/New_York")]], resize_keyboard=True,
                               one_time_keyboard=True,
                               input_field_placeholder="Or type your timezone (e.g., Europe/Berlin)")


def get_goal_text_keyboard_reg(lang: str):
    buttons = [[KeyboardButton(text=t("goal_lose_weight", lang)), KeyboardButton(text=t("goal_gain_muscle", lang))],
               [KeyboardButton(text=t("goal_eat_healthier", lang)),
                KeyboardButton(text=t("goal_look_beautiful", lang))], [KeyboardButton(text=t("skip_goal", lang))]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_goal_text_keyboard_edit(lang: str):
    buttons = [[InlineKeyboardButton(text=t("goal_lose_weight", lang), callback_data="edit_goal_select_lose_weight")],
               [InlineKeyboardButton(text=t("goal_gain_muscle", lang), callback_data="edit_goal_select_gain_muscle")],
               [InlineKeyboardButton(text=t("goal_eat_healthier", lang),
                                     callback_data="edit_goal_select_eat_healthier")],
               [InlineKeyboardButton(text=t("goal_look_beautiful", lang),
                                     callback_data="edit_goal_select_look_beautiful")],
               [InlineKeyboardButton(text=t("skip_goal", lang) + " (Clear Goal)",
                                     callback_data="edit_goal_select_skip")],
               [InlineKeyboardButton(text=t("back_to_profile_fields", lang),
                                     callback_data="edit_profile_back_to_fields")]]
    return InlineKeyboardMarkup(buttons)


def get_main_menu_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("menu_log_meal", lang)), KeyboardButton(text=t("menu_log_water", lang))],
                  [KeyboardButton(text=t("menu_settings", lang)), KeyboardButton(text=t("menu_help", lang))]],
        resize_keyboard=True)


def get_cancel_keyboard(lang: str):
    return ReplyKeyboardMarkup([[KeyboardButton(text=t("cancel_button_text", lang))]], resize_keyboard=True,
                               one_time_keyboard=True)


def get_calendar_keyboard_placeholder(lang: str):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Calendar (Not Implemented)", callback_data="calendar_noop")]])


def get_meal_type_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("breakfast", lang)), KeyboardButton(text=t("lunch", lang))],
            [KeyboardButton(text=t("dinner", lang)), KeyboardButton(text=t("snack", lang))],
            [KeyboardButton(text=t("general_meal", lang)), KeyboardButton(text=t("cancel_button_text", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=t("log_meal_type_select", lang)  # Add placeholder text
    )


# ==================== Conversation States ====================
(SELECT_LANG, ASK_NAME, ASK_AGE, ASK_HEIGHT, ASK_WEIGHT, ASK_GENDER,
 ASK_TIMEZONE, ASK_GOAL_TEXT, ASK_CALORIE_GOAL, ASK_DREAM_WEIGHT, AWAIT_MEAL_TYPE, AWAIT_MEAL_INPUT) = range(12)
(SETTINGS_MAIN, CHANGE_LANGUAGE_SELECT,EDIT_PROFILE_SELECT_FIELD, EDIT_PROFILE_ENTER_VALUE, EDIT_PROFILE_SELECT_GOAL,
 EDIT_REMINDERS_MENU) = range(13, 19)
logger.info("Conversation states defined.")


# ==================== Reminder & Motivational Message Functions ====================
async def schedule_user_reminders_task(user_id: int, user_timezone_str: str, lang: str, bot_instance: Bot):
    global scheduler
    if not db:
        logger.warning(f"DB not available in schedule_user_reminders_task for user {user_id}.")
        return
    if not scheduler:
        logger.error(f"Scheduler not initialized in schedule_user_reminders_task for user {user_id}.")
        return
    user_ref = get_user_ref(user_id)
    if not user_ref:
        return
    try:
        user_data_snap = await asyncio.to_thread(user_ref.get)
    except Exception as e:
        logger.error(f"DB error fetching user data for reminders {user_id}: {e}")
        return
    if not user_data_snap.exists:
        logger.warning(f"Cannot schedule reminders for user {user_id}: data not found.")
        return
    user_data = user_data_snap.to_dict()
    try:
        user_timezone = pytz.timezone(user_timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone '{user_timezone_str}' for user {user_id}. Using UTC.")
        user_timezone = pytz.utc
    for job in scheduler.get_jobs():
        if job.id and (job.id.startswith(f"water_reminder_{user_id}_") or
                       job.id.startswith(f"meal_reminder_{user_id}_") or
                       job.id.startswith(f"motivation_{user_id}")):
            try:
                scheduler.remove_job(job.id)
            except Exception as e_rem:
                logger.warning(f"Could not remove job {job.id} for user {user_id}: {e_rem}")
    if user_data.get('water_reminders', True):
        for hour_local in range(8, 23, 2):
            job_id = f"water_reminder_{user_id}_{hour_local}"
            try:
                scheduler.add_job(send_water_reminder_task, 'cron', hour=hour_local, timezone=user_timezone,
                                  args=[user_id, bot_instance], id=job_id, replace_existing=True,
                                  misfire_grace_time=300)
            except Exception as e:
                logger.error(f"Error scheduling water reminder job {job_id} for user {user_id}: {e}")
    if user_data.get('meal_reminders', True):
        meal_times_local = [("09:00", "breakfast"), ("13:00", "lunch"), ("19:00", "dinner")]
        for time_str, meal_type_key in meal_times_local:
            hour_local, minute_local = map(int, time_str.split(':'))
            job_id = f"meal_reminder_{user_id}_{meal_type_key}"
            try:
                scheduler.add_job(send_meal_reminder_task, 'cron', hour=hour_local, minute=minute_local,
                                  timezone=user_timezone, args=[user_id, meal_type_key, bot_instance], id=job_id,
                                  replace_existing=True, misfire_grace_time=300)
            except Exception as e:
                logger.error(f"Error scheduling meal reminder job {job_id} for user {user_id}: {e}")
    job_id_motivation = f"motivation_{user_id}"
    try:
        scheduler.add_job(send_daily_motivation_task, 'cron', hour=10, minute=0, timezone=user_timezone,
                          args=[user_id, bot_instance], id=job_id_motivation, replace_existing=True,
                          misfire_grace_time=3600)
    except Exception as e:
        logger.error(f"Error scheduling motivational message for user {user_id}: {e}")
    logger.info(f"Scheduled/Rescheduled reminders and motivation for user {user_id} in timezone {user_timezone_str}")


async def send_water_reminder_task(user_id: int, bot_instance: Bot):
    lang = await get_user_language_db(user_id)
    message_text = t("water_reminder", lang)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=t("menu_log_water", lang), callback_data="log_water_from_reminder")]])
    try:
        await bot_instance.send_message(chat_id=user_id, text=message_text, reply_markup=keyboard)
        logger.info(f"Sent water reminder to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending water reminder to user {user_id}: {e}")


async def send_meal_reminder_task(user_id: int, meal_type_key: str, bot_instance: Bot):
    lang = await get_user_language_db(user_id)
    meal_type_display = t(meal_type_key, lang)
    message_text = t("meal_reminder", lang, meal_type=meal_type_display)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=t("menu_log_meal", lang) + f" ({meal_type_display})",
                                                           callback_data=f"log_meal_general_from_reminder_{meal_type_key}")]])
    try:
        await bot_instance.send_message(chat_id=user_id, text=message_text, reply_markup=keyboard)
        logger.info(f"Sent meal reminder for {meal_type_key} to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending meal reminder for {meal_type_key} to user {user_id}: {e}")


async def send_daily_motivation_task(user_id: int, bot_instance: Bot):
    if not db:
        return
    user_ref = get_user_ref(user_id)
    if not user_ref:
        return
    try:
        user_doc_snap = await asyncio.to_thread(user_ref.get)
        if not user_doc_snap.exists:
            logger.warning(f"User {user_id} not found for motivational message.")
            return
        user_data = user_doc_snap.to_dict()
        lang = user_data.get('language', 'en')
        name = user_data.get('name', 'User')
        motivation_text = "Remember your health goals today! You can do it!"
        daily_calorie_goal = user_data.get('daily_calorie_goal')
        if daily_calorie_goal and isinstance(daily_calorie_goal, (int, float)) and daily_calorie_goal > 0:
            user_timezone = pytz.timezone(user_data.get('timezone', 'UTC'))
            yesterday_local = datetime.now(user_timezone).date() - timedelta(days=1)
            start_utc, end_utc = get_day_utc_boundaries(yesterday_local, user_timezone)
            meals_ref = get_meals_ref(user_id)
            if meals_ref:
                yesterdays_meals_snap = await asyncio.to_thread(lambda: list(
                    meals_ref.where('timestamp', '>=', start_utc).where('timestamp', '<=', end_utc).stream()))
                calories_yesterday = sum(doc.to_dict().get('calories_estimated', 0) for doc in yesterdays_meals_snap if
                                         doc.to_dict().get('calories_estimated') is not None)
                if calories_yesterday == 0:
                    motivation_text = "Don't forget to log your meals today to track your progress!"
                elif calories_yesterday < daily_calorie_goal * 0.8:
                    motivation_text = f"You were a bit under your calorie goal yesterday ({calories_yesterday}/{int(daily_calorie_goal)}). Let's aim to fuel up well today!"
                elif calories_yesterday > daily_calorie_goal * 1.2:
                    motivation_text = f"Yesterday's calories ({calories_yesterday}/{int(daily_calorie_goal)}) were a bit over. A fresh start today!"
                else:
                    motivation_text = f"Great job staying near your goal yesterday ({calories_yesterday}/{int(daily_calorie_goal)})! Keep up the amazing work!"
        full_message = t("daily_motivation_template", lang, name=name, message=motivation_text)
        await bot_instance.send_message(chat_id=user_id, text=full_message)
        logger.info(f"Sent daily motivation to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending daily motivation to user {user_id}: {e}", exc_info=True)


# ==================== Registration Conversation ====================
async def start_command(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    if not db:
        await update.message.reply_text("Database service is currently unavailable. Please try again later.")
        return ConversationHandler.END
    user_ref = get_user_ref(user.id)
    if not user_ref:
        await update.message.reply_text("Error accessing user data. Please try again later.")
        return ConversationHandler.END
    user_doc = await asyncio.to_thread(user_ref.get)
    if user_doc.exists:
        lang = user_doc.to_dict().get('language', 'en')
        context.user_data['language'] = lang
        await update.message.reply_text(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(t("intro", "en"), reply_markup=get_language_keyboard_reg())
    return SELECT_LANG


async def select_lang_reg(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    lang_code = "en"
    if "O'zbek" in text or "🇺🇿" in text:
        lang_code = "uz"
    elif "Русский" in text or "🇷🇺" in text:
        lang_code = "ru"
    elif "English" in text or "🇬🇧" in text:
        lang_code = "en"
    else:
        await update.message.reply_text(t("select_language", "en"), reply_markup=get_language_keyboard_reg())
        return SELECT_LANG
    context.user_data['language'] = lang_code
    await update.message.reply_text(t("language_selected_message", lang_code) + "\n" + t("ask_name", lang_code),
                                    reply_markup=get_cancel_keyboard(lang_code))
    return ASK_NAME


async def ask_name_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    name = update.message.text.strip()
    if not (2 <= len(name) <= 50):
        await update.message.reply_text(t("name_error", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_NAME
    context.user_data['name'] = name
    await update.message.reply_text(t("ask_age", lang), reply_markup=get_cancel_keyboard(lang))
    return ASK_AGE


async def ask_age_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    try:
        age = int(update.message.text.strip())
        if not (0 <= age <= 120):
            raise ValueError("Invalid age range")
        context.user_data['age'] = age
        await update.message.reply_text(t("ask_height", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_HEIGHT
    except ValueError:
        await update.message.reply_text(t("age_error", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_AGE


async def ask_height_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    try:
        height = float(update.message.text.strip().replace(',', '.'))
        if not (50 <= height <= 250):
            raise ValueError("Invalid height range")
        context.user_data['height'] = height
        await update.message.reply_text(t("ask_weight", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_WEIGHT
    except ValueError:
        await update.message.reply_text(t("height_error", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_HEIGHT


async def ask_weight_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    try:
        weight = float(update.message.text.strip().replace(',', '.'))
        if not (20 <= weight <= 300):
            raise ValueError("Invalid weight range")
        context.user_data['weight'] = weight
        await update.message.reply_text(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))
        return ASK_GENDER
    except ValueError:
        await update.message.reply_text(t("weight_error", lang), reply_markup=get_cancel_keyboard(lang))
        return ASK_WEIGHT


async def ask_gender_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    text_lower = update.message.text.strip().lower()
    gender = None
    if t("male", lang).lower() in text_lower:
        gender = "male"
    elif t("female", lang).lower() in text_lower:
        gender = "female"
    if not gender:
        await update.message.reply_text(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))
        return ASK_GENDER
    context.user_data['gender'] = gender
    await update.message.reply_text(t("ask_timezone", lang), reply_markup=get_timezone_keyboard())
    return ASK_TIMEZONE


async def ask_timezone_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    tz_str = update.message.text.strip()
    try:
        pytz.timezone(tz_str)
        context.user_data['timezone'] = tz_str
        await update.message.reply_text(t("ask_goal_text", lang), reply_markup=get_goal_text_keyboard_reg(lang))
        return ASK_GOAL_TEXT
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(t("timezone_error", lang), reply_markup=get_timezone_keyboard())
        return ASK_TIMEZONE


async def ask_goal_text_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    goal_input = update.message.text.strip()
    predefined_goals_keys = ["goal_lose_weight", "goal_gain_muscle", "goal_eat_healthier", "goal_look_beautiful",
                             "skip_goal"]
    selected_goal = ""
    for key in predefined_goals_keys:
        if goal_input.lower() == t(key, lang).lower():
            selected_goal = t(key, "en")
            break
    if selected_goal == t("skip_goal", "en") or not selected_goal:
        context.user_data['goal_text'] = goal_input if selected_goal != t("skip_goal", "en") else ""
    else:
        context.user_data['goal_text'] = selected_goal
    await update.message.reply_text(t("ask_calorie_goal", lang), reply_markup=get_cancel_keyboard(lang))
    return ASK_CALORIE_GOAL


async def ask_calorie_goal_reg(update: Update, context: CallbackContext) -> int:
    lang = context.user_data.get('language', 'en')
    calorie_input = update.message.text.strip().lower()
    if calorie_input == "skip" or calorie_input == t("skip_goal", lang).lower():
        context.user_data['daily_calorie_goal'] = None
        estimated_calories = estimate_daily_calories(context.user_data.get('weight'), context.user_data.get('height'),
                                                     context.user_data.get('age'), context.user_data.get('gender'),
                                                     context.user_data.get('goal_text', ""), None)
        if estimated_calories:
            context.user_data['daily_calorie_goal'] = estimated_calories
            await update.message.reply_text(
                f"Based on your info, we've estimated your daily calorie goal at {estimated_calories} kcal. You can change this later in settings.")
        else:
            await update.message.reply_text("Okay, you can set your calorie goal later in settings.")
    else:
        try:
            calories = int(calorie_input)
            if not (500 <= calories <= 10000):
                raise ValueError("Unrealistic calorie goal")
            context.user_data['daily_calorie_goal'] = calories
        except ValueError:
            await update.message.reply_text(t("calorie_goal_error", lang), reply_markup=get_cancel_keyboard(lang))
            return ASK_CALORIE_GOAL
    await update.message.reply_text(t("ask_dream_weight", lang), reply_markup=get_cancel_keyboard(lang))
    return ASK_DREAM_WEIGHT


async def ask_dream_weight_reg(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    lang = context.user_data.get('language', 'en')
    dream_weight_input = update.message.text.strip().lower()
    if dream_weight_input == t("skip_goal", lang).lower() or dream_weight_input == "skip":
        context.user_data['dream_weight'] = None
    else:
        try:
            dream_weight_val = float(dream_weight_input.replace(',', '.'))
            if not (20 <= dream_weight_val <= 300):
                raise ValueError("Invalid dream weight")
            context.user_data['dream_weight'] = dream_weight_val
        except ValueError:
            await update.message.reply_text(t("dream_weight_error", lang), reply_markup=get_cancel_keyboard(lang))
            return ASK_DREAM_WEIGHT
    final_user_data = {
        'language': lang,
        'name': context.user_data.get('name'),
        'age': context.user_data.get('age'),
        'height': context.user_data.get('height'),
        'weight': context.user_data.get('weight'),
        'gender': context.user_data.get('gender'),
        'timezone': context.user_data.get('timezone'),
        'goal_text': context.user_data.get('goal_text', ""),
        'daily_calorie_goal': context.user_data.get('daily_calorie_goal'),
        'dream_weight': context.user_data.get('dream_weight'),
        'registered_at': firestore.SERVER_TIMESTAMP,
        'telegram_username': user.username or "",
        'telegram_id': user.id,
        'last_active': firestore.SERVER_TIMESTAMP,
        'water_reminders': True,
        'meal_reminders': True
    }
    user_ref = get_user_ref(user.id)
    if not user_ref:
        await update.message.reply_text(t("error_processing", lang) + " (DB_FAIL_REG_FINAL)",
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    try:
        await asyncio.to_thread(user_ref.set, final_user_data)
        logger.info(f"User {user.id} registration complete. Data: {final_user_data}")
        await schedule_user_reminders_task(user.id, final_user_data['timezone'], lang, context.bot)
        await update.message.reply_text(t("registration_complete", lang), reply_markup=get_main_menu_keyboard(lang))
        context.user_data.clear()
        context.user_data['language'] = lang
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Registration finalization error for user {user.id}: {e}", exc_info=True)
        await update.message.reply_text(t("error_processing", lang) + " (REG_SAVE_FAIL)",
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def cancel_flow(update: Update, context: CallbackContext, flow_name: str = "action") -> int:
    lang = await get_user_language_db(update.effective_user.id, context)
    cancel_message_key = "registration_cancelled" if flow_name == "registration" else "action_cancelled"
    main_menu_text = t("main_menu", lang)
    main_menu_kb = get_main_menu_keyboard(lang)
    if update.message:
        await update.message.reply_text(t(cancel_message_key, lang) + "\n" + main_menu_text, reply_markup=main_menu_kb)
    elif update.callback_query:
        await update.callback_query.answer(t(cancel_message_key, lang))
        try:
            await update.callback_query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=t(cancel_message_key, lang) + "\n" + main_menu_text,
                                       reply_markup=main_menu_kb)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_registration_conv(update: Update, context: CallbackContext):
    return await cancel_flow(update, context, "registration")


async def cancel_meal_log_conv(update: Update, context: CallbackContext):
    return await cancel_flow(update, context, "meal_logging")


def registration_conversation() -> ConversationHandler:
    cancel_texts = [t("cancel_button_text", lang) for lang in ["en", "ru", "uz"]]
    cancel_pattern = f"^({'|'.join(re.escape(text) for text in cancel_texts)})$"
    return ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            SELECT_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_lang_reg)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_name_reg)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_age_reg)],
            ASK_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_height_reg)],
            ASK_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_weight_reg)],
            ASK_GENDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_gender_reg)],
            ASK_TIMEZONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_timezone_reg)],
            ASK_GOAL_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_goal_text_reg)],
            ASK_CALORIE_GOAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_calorie_goal_reg)],
            ASK_DREAM_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern), ask_dream_weight_reg)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_registration_conv),
            MessageHandler(filters.Regex(cancel_pattern), cancel_registration_conv)
        ],
        name="registration",
        persistent=True
    )


# ==================== Settings Conversation ====================
async def settings_entry_command_or_button(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await update.message.reply_text(t("not_registered", lang))
        await start_command(update, context)
        return ConversationHandler.END
    settings_kb_buttons = [
        [InlineKeyboardButton(text=t("change_language", lang), callback_data="settings_change_language")],
        [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="settings_edit_profile")],
        [InlineKeyboardButton(text=t("edit_reminders", lang), callback_data="settings_edit_reminders")],
        [InlineKeyboardButton(text=t("back_to_menu", lang), callback_data="settings_back_to_main_menu")]
    ]
    await update.message.reply_text(t("settings_title", lang), reply_markup=InlineKeyboardMarkup(settings_kb_buttons))
    return SETTINGS_MAIN


async def settings_main_callback_handler(update: Update, context: CallbackContext) -> Optional[int]:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_user_language_db(user_id, context)
    if query.data == "settings_back_to_main_menu":
        await query.edit_message_text(t("main_menu", lang), reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text=t("main_menu", lang),
                                       reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END
    elif query.data == "settings_change_language":
        await query.edit_message_text(t("select_new_language", lang), reply_markup=get_language_keyboard_reg())
        return CHANGE_LANGUAGE_SELECT
    elif query.data == "settings_edit_profile":
        buttons = [
            [InlineKeyboardButton(t("edit_name", lang), callback_data="edit_field_name")],
            [InlineKeyboardButton(t("edit_age", lang), callback_data="edit_field_age")],
            [InlineKeyboardButton(t("edit_height", lang), callback_data="edit_field_height")],
            [InlineKeyboardButton(t("edit_weight", lang), callback_data="edit_field_weight")],
            [InlineKeyboardButton(t("edit_goal_text", lang), callback_data="edit_field_goal_text")],
            [InlineKeyboardButton(t("edit_calorie_goal", lang), callback_data="edit_field_daily_calorie_goal")],
            [InlineKeyboardButton(t("edit_dream_weight", lang), callback_data="edit_field_dream_weight")],
            [InlineKeyboardButton(t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ]
        await query.edit_message_text(t("edit_which_field", lang), reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_PROFILE_SELECT_FIELD
    elif query.data == "settings_edit_reminders":
        user_ref = get_user_ref(user_id)
        user_data_snap = await asyncio.to_thread(user_ref.get) if user_ref else None
        user_data = user_data_snap.to_dict() if user_data_snap and user_data_snap.exists else {}
        water_on = user_data.get('water_reminders', True)
        meal_on = user_data.get('meal_reminders', True)
        ws_display = t("on_status" if water_on else "off_status", lang)
        ms_display = t("on_status" if meal_on else "off_status", lang)
        reminders_text = t("reminder_settings_text", lang, water_status=ws_display, meal_status=ms_display)
        reminders_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                text=f"{t('toggle_water_reminders', lang)}{t('reminder_on_off_template', lang, status=t('off_status' if water_on else 'on_status', lang))}",
                callback_data="reminders_toggle_water")],
            [InlineKeyboardButton(
                text=f"{t('toggle_meal_reminders', lang)}{t('reminder_on_off_template', lang, status=t('off_status' if meal_on else 'on_status', lang))}",
                callback_data="reminders_toggle_meal")],
            [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ])
        await query.edit_message_text(reminders_text, reply_markup=reminders_kb)
        return EDIT_REMINDERS_MENU
    return SETTINGS_MAIN


async def change_language_selected(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    text = update.message.text
    lang_code = "en"
    if "O'zbek" in text or "🇺🇿" in text:
        lang_code = "uz"
    elif "Русский" in text or "🇷🇺" in text:
        lang_code = "ru"
    elif "English" in text or "🇬🇧" in text:
        lang_code = "en"
    else:
        lang = await get_user_language_db(user_id, context)
        await update.message.reply_text(t("select_new_language", lang), reply_markup=get_language_keyboard_reg())
        return CHANGE_LANGUAGE_SELECT
    user_ref = get_user_ref(user_id)
    if user_ref:
        await asyncio.to_thread(user_ref.update, {'language': lang_code, 'last_active': firestore.SERVER_TIMESTAMP})
    context.user_data['language'] = lang_code
    await update.message.reply_text(t("language_changed", lang_code), reply_markup=get_main_menu_keyboard(lang_code))
    return ConversationHandler.END


async def edit_profile_select_field_handler(update: Update, context: CallbackContext) -> Optional[int]:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_user_language_db(user_id, context)
    if query.data == "settings_back_to_settings_menu":
        settings_kb_buttons = [
            [InlineKeyboardButton(text=t("change_language", lang), callback_data="settings_change_language")],
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="settings_edit_profile")],
            [InlineKeyboardButton(text=t("edit_reminders", lang), callback_data="settings_edit_reminders")],
            [InlineKeyboardButton(text=t("back_to_menu", lang), callback_data="settings_back_to_main_menu")]
        ]
        await query.edit_message_text(t("settings_title", lang), reply_markup=InlineKeyboardMarkup(settings_kb_buttons))
        return SETTINGS_MAIN
    elif query.data.startswith("edit_field_"):
        field_name = query.data.replace("edit_field_", "")
        context.user_data['editing_field'] = field_name
        if field_name == "goal_text":
            await query.edit_message_text(t("ask_goal_text", lang), reply_markup=get_goal_text_keyboard_edit(lang))
            return EDIT_PROFILE_SELECT_GOAL
        user_ref = get_user_ref(user_id)
        user_data_snap = await asyncio.to_thread(user_ref.get) if user_ref else None
        user_data = user_data_snap.to_dict() if user_data_snap and user_data_snap.exists else {}
        current_value = user_data.get(field_name, t("not_available", lang))
        field_display = t(f"field_name_{field_name}", lang)
        await query.edit_message_text(
            f"{t('enter_new_value', lang, field=field_display)}\n{t('current_value_is', lang)}: {current_value}",
            reply_markup=get_cancel_keyboard(lang)
        )
        return EDIT_PROFILE_ENTER_VALUE
    return EDIT_PROFILE_SELECT_FIELD


async def edit_profile_select_goal_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_user_language_db(user_id, context)
    if query.data == "edit_profile_back_to_fields":
        buttons = [
            [InlineKeyboardButton(t("edit_name", lang), callback_data="edit_field_name")],
            [InlineKeyboardButton(t("edit_age", lang), callback_data="edit_field_age")],
            [InlineKeyboardButton(t("edit_height", lang), callback_data="edit_field_height")],
            [InlineKeyboardButton(t("edit_weight", lang), callback_data="edit_field_weight")],
            [InlineKeyboardButton(t("edit_goal_text", lang), callback_data="edit_field_goal_text")],
            [InlineKeyboardButton(t("edit_calorie_goal", lang), callback_data="edit_field_daily_calorie_goal")],
            [InlineKeyboardButton(t("edit_dream_weight", lang), callback_data="edit_field_dream_weight")],
            [InlineKeyboardButton(t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ]
        await query.edit_message_text(t("edit_which_field", lang), reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_PROFILE_SELECT_FIELD
    elif query.data.startswith("edit_goal_select_"):
        goal_key = query.data.replace("edit_goal_select_", "")
        goal_map = {
            "lose_weight": t("goal_lose_weight", "en"),
            "gain_muscle": t("goal_gain_muscle", "en"),
            "eat_healthier": t("goal_eat_healthier", "en"),
            "look_beautiful": t("goal_look_beautiful", "en"),
            "skip": ""
        }
        selected_goal = goal_map.get(goal_key, "")
        user_ref = get_user_ref(user_id)
        if user_ref:
            await asyncio.to_thread(user_ref.update, {
                'goal_text': selected_goal,
                'last_active': firestore.SERVER_TIMESTAMP
            })
        await query.edit_message_text(t("profile_updated", lang))
        buttons = [
            [InlineKeyboardButton(t("edit_name", lang), callback_data="edit_field_name")],
            [InlineKeyboardButton(t("edit_age", lang), callback_data="edit_field_age")],
            [InlineKeyboardButton(t("edit_height", lang), callback_data="edit_field_height")],
            [InlineKeyboardButton(t("edit_weight", lang), callback_data="edit_field_weight")],
            [InlineKeyboardButton(t("edit_goal_text", lang), callback_data="edit_field_goal_text")],
            [InlineKeyboardButton(t("edit_calorie_goal", lang), callback_data="edit_field_daily_calorie_goal")],
            [InlineKeyboardButton(t("edit_dream_weight", lang), callback_data="edit_field_dream_weight")],
            [InlineKeyboardButton(t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text=t("edit_which_field", lang),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return EDIT_PROFILE_SELECT_FIELD
    return EDIT_PROFILE_SELECT_GOAL


async def edit_profile_enter_value_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    field_name = context.user_data.get('editing_field')
    if not field_name:
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END
    user_input = update.message.text.strip()
    user_ref = get_user_ref(user_id)
    if not user_ref:
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END
    try:
        update_data = {'last_active': firestore.SERVER_TIMESTAMP}
        if field_name == "name":
            if not (2 <= len(user_input) <= 50):
                await update.message.reply_text(t("name_error", lang), reply_markup=get_cancel_keyboard(lang))
                return EDIT_PROFILE_ENTER_VALUE
            update_data['name'] = user_input
        elif field_name == "age":
            try:
                age = int(user_input)
                if not (0 <= age <= 120):
                    raise ValueError
                update_data['age'] = age
            except ValueError:
                await update.message.reply_text(t("age_error", lang), reply_markup=get_cancel_keyboard(lang))
                return EDIT_PROFILE_ENTER_VALUE
        elif field_name == "height":
            try:
                height = float(user_input.replace(',', '.'))
                if not (50 <= height <= 250):
                    raise ValueError
                update_data['height'] = height
            except ValueError:
                await update.message.reply_text(t("height_error", lang), reply_markup=get_cancel_keyboard(lang))
                return EDIT_PROFILE_ENTER_VALUE
        elif field_name == "weight":
            try:
                weight = float(user_input.replace(',', '.'))
                if not (20 <= weight <= 300):
                    raise ValueError
                update_data['weight'] = weight
            except ValueError:
                await update.message.reply_text(t("weight_error", lang), reply_markup=get_cancel_keyboard(lang))
                return EDIT_PROFILE_ENTER_VALUE
        elif field_name == "daily_calorie_goal":
            if user_input.lower() in ["skip", t("skip_goal", lang).lower()]:
                update_data['daily_calorie_goal'] = None
            else:
                try:
                    calories = int(user_input)
                    if not (500 <= calories <= 10000):
                        raise ValueError
                    update_data['daily_calorie_goal'] = calories
                except ValueError:
                    await update.message.reply_text(t("calorie_goal_error", lang),
                                                    reply_markup=get_cancel_keyboard(lang))
                    return EDIT_PROFILE_ENTER_VALUE
        elif field_name == "dream_weight":
            if user_input.lower() in ["skip", t("skip_goal", lang).lower()]:
                update_data['dream_weight'] = None
            else:
                try:
                    dream_weight = float(user_input.replace(',', '.'))
                    if not (20 <= dream_weight <= 300):
                        raise ValueError
                    update_data['dream_weight'] = dream_weight
                except ValueError:
                    await update.message.reply_text(t("dream_weight_error", lang),
                                                    reply_markup=get_cancel_keyboard(lang))
                    return EDIT_PROFILE_ENTER_VALUE
        await asyncio.to_thread(user_ref.update, update_data)
        await update.message.reply_text(t("profile_updated", lang))
        buttons = [
            [InlineKeyboardButton(t("edit_name", lang), callback_data="edit_field_name")],
            [InlineKeyboardButton(t("edit_age", lang), callback_data="edit_field_age")],
            [InlineKeyboardButton(t("edit_height", lang), callback_data="edit_field_height")],
            [InlineKeyboardButton(t("edit_weight", lang), callback_data="edit_field_weight")],
            [InlineKeyboardButton(t("edit_goal_text", lang), callback_data="edit_field_goal_text")],
            [InlineKeyboardButton(t("edit_calorie_goal", lang), callback_data="edit_field_daily_calorie_goal")],
            [InlineKeyboardButton(t("edit_dream_weight", lang), callback_data="edit_field_dream_weight")],
            [InlineKeyboardButton(t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text=t("edit_which_field", lang),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        context.user_data.pop('editing_field', None)
        return EDIT_PROFILE_SELECT_FIELD
    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}, field {field_name}: {e}", exc_info=True)
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END


async def edit_reminders_menu_handler(update: Update, context: CallbackContext) -> Optional[int]:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref:
        await query.edit_message_text(t("error_processing", lang))
        return ConversationHandler.END
    user_data_snap = await asyncio.to_thread(user_ref.get)
    user_data = user_data_snap.to_dict() if user_data_snap.exists else {}
    if query.data == "settings_back_to_settings_menu":
        settings_kb_buttons = [
            [InlineKeyboardButton(text=t("change_language", lang), callback_data="settings_change_language")],
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="settings_edit_profile")],
            [InlineKeyboardButton(text=t("edit_reminders", lang), callback_data="settings_edit_reminders")],
            [InlineKeyboardButton(text=t("back_to_menu", lang), callback_data="settings_back_to_main_menu")]
        ]
        await query.edit_message_text(t("settings_title", lang), reply_markup=InlineKeyboardMarkup(settings_kb_buttons))
        return SETTINGS_MAIN
    elif query.data in ["reminders_toggle_water", "reminders_toggle_meal"]:
        field = 'water_reminders' if query.data == "reminders_toggle_water" else 'meal_reminders'
        current_status = user_data.get(field, True)
        new_status = not current_status
        action_name = t("toggle_water_reminders" if field == "water_reminders" else "toggle_meal_reminders", lang)
        try:
            await asyncio.to_thread(user_ref.update, {field: new_status, 'last_active': firestore.SERVER_TIMESTAMP})
            user_timezone = user_data.get('timezone', 'UTC')
            await schedule_user_reminders_task(user_id, user_timezone, lang, context.bot)
            await query.answer(t("reminder_toggled_alert", lang, action=action_name,
                                 status=t("on_status" if new_status else "off_status", lang)))
            user_data[field] = new_status
        except Exception as e:
            logger.error(f"Error toggling {field} for user {user_id}: {e}", exc_info=True)
            await query.answer(t("error_processing", lang))
        water_on = user_data.get('water_reminders', True)
        meal_on = user_data.get('meal_reminders', True)
        ws_display = t("on_status" if water_on else "off_status", lang)
        ms_display = t("on_status" if meal_on else "off_status", lang)
        reminders_text = t("reminder_settings_text", lang, water_status=ws_display, meal_status=ms_display)
        reminders_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                text=f"{t('toggle_water_reminders', lang)}{t('reminder_on_off_template', lang, status=t('off_status' if water_on else 'on_status', lang))}",
                callback_data="reminders_toggle_water")],
            [InlineKeyboardButton(
                text=f"{t('toggle_meal_reminders', lang)}{t('reminder_on_off_template', lang, status=t('off_status' if meal_on else 'on_status', lang))}",
                callback_data="reminders_toggle_meal")],
            [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="settings_back_to_settings_menu")]
        ])
        await query.edit_message_text(reminders_text, reply_markup=reminders_kb)
        return EDIT_REMINDERS_MENU
    return EDIT_REMINDERS_MENU


async def settings_cancel(update: Update, context: CallbackContext) -> int:
    return await cancel_flow(update, context, "settings")


def settings_conversation() -> ConversationHandler:
    cancel_texts = [t("cancel_button_text", lang) for lang in ["en", "ru", "uz"]]
    cancel_pattern = f"^({'|'.join(re.escape(text) for text in cancel_texts)})$"
    return ConversationHandler(
        entry_points=[
            CommandHandler('settings', settings_entry_command_or_button),
            MessageHandler(filters.Regex(
                f"^{t('menu_settings', 'en')}$|^{t('menu_settings', 'ru')}$|^{t('menu_settings', 'uz')}$"),
                           settings_entry_command_or_button)
        ],
        states={
            SETTINGS_MAIN: [CallbackQueryHandler(settings_main_callback_handler, pattern="^settings_.*$")],
            CHANGE_LANGUAGE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_language_selected)],
            EDIT_PROFILE_SELECT_FIELD: [
                CallbackQueryHandler(edit_profile_select_field_handler, pattern="^edit_field_.*$|^settings_.*$")],
            EDIT_PROFILE_ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern),
                                                      edit_profile_enter_value_handler)],
            EDIT_PROFILE_SELECT_GOAL: [CallbackQueryHandler(edit_profile_select_goal_handler,
                                                            pattern="^edit_goal_select_.*$|^edit_profile_back_to_fields$")],
            EDIT_REMINDERS_MENU: [
                CallbackQueryHandler(edit_reminders_menu_handler, pattern="^reminders_toggle_.*$|^settings_.*$")]
        },
        fallbacks=[
            CommandHandler('cancel', settings_cancel),
            MessageHandler(filters.Regex(cancel_pattern), settings_cancel)
        ],
        name="settings",
        persistent=True
    )


# ==================== Meal Logging Conversation ====================
async def log_meal_entry(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await update.message.reply_text(t("not_registered", lang))
        await start_command(update, context)
        return ConversationHandler.END
    await update.message.reply_text(t("log_meal_type_select", lang), reply_markup=get_meal_type_keyboard(lang))
    return AWAIT_MEAL_TYPE


async def log_meal_from_reminder(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await query.edit_message_text(t("not_registered", lang))
        await start_command(update, context)
        return ConversationHandler.END
    if query.data.startswith("log_meal_general_from_reminder_"):
        meal_type_key = query.data.replace("log_meal_general_from_reminder_", "")
        context.user_data['meal_type'] = meal_type_key
        await query.edit_message_text(t("ask_log_meal_general", lang, meal_type=t(meal_type_key, lang)),
                                      reply_markup=get_cancel_keyboard(lang))
        return AWAIT_MEAL_INPUT
    return ConversationHandler.END


async def await_meal_type_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    text = update.message.text.strip()

    # Clear any previous meal type
    context.user_data.pop('meal_type', None)

    # Map localized button text to meal type keys
    meal_mapping = {
        t("breakfast", lang).lower(): "breakfast",
        t("lunch", lang).lower(): "lunch",
        t("dinner", lang).lower(): "dinner",
        t("snack", lang).lower(): "snack",
        t("general_meal", lang).lower(): "general_meal",
        t("cancel_button_text", lang).lower(): "cancel"
    }

    selected_meal = meal_mapping.get(text.lower())

    if selected_meal == "cancel":
        return await cancel_meal_log_conv(update, context)
    if not selected_meal:
        await update.message.reply_text(t("log_meal_type_select", lang),
                                        reply_markup=get_meal_type_keyboard(lang))
        return AWAIT_MEAL_TYPE

    context.user_data['meal_type'] = selected_meal
    await update.message.reply_text(
        t("ask_log_meal_general", lang, meal_type=t(selected_meal, lang)),
        reply_markup=get_cancel_keyboard(lang)
    )
    return AWAIT_MEAL_INPUT


async def await_meal_input_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    meal_type = context.user_data.get('meal_type', 'general_meal')
    user_ref = get_user_ref(user_id)
    if not user_ref:
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END
    food_description = update.message.text if update.message.text else ""
    photo_bytes = None
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
    if not (food_description or photo_bytes):
        await update.message.reply_text(t("ask_log_meal_general", lang, meal_type=t(meal_type, lang)),
                                        reply_markup=get_cancel_keyboard(lang))
        return AWAIT_MEAL_INPUT
    await update.message.reply_text(t("processing", lang), reply_markup=ReplyKeyboardRemove())
    try:
        analysis = await process_food_input(food_description, photo_bytes, lang)
        meal_data = {
            'food_name': analysis.get('food_name', 'Unknown'),
            'calories_estimated': analysis.get('calories_estimated', 0),
            'protein_g': analysis.get('protein_g', 0),
            'carbs_g': analysis.get('carbs_g', 0),
            'fat_g': analysis.get('fat_g', 0),
            'micronutrients': analysis.get('micronutrients', []),
            'positive_points': analysis.get('positive_points', []),
            'negative_points': analysis.get('negative_points', []),
            'meal_type': meal_type,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'description': food_description,
            'has_photo': bool(photo_bytes)
        }
        meals_ref = get_meals_ref(user_id)
        if meals_ref:
            await asyncio.to_thread(meals_ref.add, meal_data)
        analysis_text = t("food_analysis_header", lang, food_name=meal_data['food_name'])
        analysis_text += f"🔥 {t('stats_calories', lang)}: {meal_data['calories_estimated']} kcal\n"
        analysis_text += f"🍗 {t('protein', lang)}: {meal_data['protein_g']}g\n"
        analysis_text += f"🍞 {t('carbohydrates', lang)}: {meal_data['carbs_g']}g\n"
        analysis_text += f"🧈 {t('fat', lang)}: {meal_data['fat_g']}g\n"
        if meal_data['micronutrients']:
            analysis_text += f"🔬 {t('micronutrients', lang)}: {', '.join(meal_data['micronutrients'])}\n"
        analysis_text += f"\n{t('food_boast_text', lang)}\n"
        if meal_data['positive_points']:
            analysis_text += f"✅ {t('positive_side_label', lang)}: {'; '.join(meal_data['positive_points'])}\n"
        if meal_data['negative_points']:
            analysis_text += f"⚠️ {t('negative_side_label', lang)}: {'; '.join(meal_data['negative_points'])}\n"
        await update.message.reply_text(analysis_text, parse_mode=ParseMode.HTML,
                                        reply_markup=get_main_menu_keyboard(lang))
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error processing meal input for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        return ConversationHandler.END


def meal_logging_conversation() -> ConversationHandler:
    cancel_texts = [t("cancel_button_text", lang) for lang in ["en", "ru", "uz"]]
    cancel_pattern = f"^({'|'.join(re.escape(text) for text in cancel_texts)})$"
    return ConversationHandler(
        entry_points=[
            CommandHandler('logmeal', log_meal_entry),
            MessageHandler(filters.Regex(
                f"^{t('menu_log_meal', 'en')}$|^{t('menu_log_meal', 'ru')}$|^{t('menu_log_meal', 'uz')}$"),
                           log_meal_entry),
            CallbackQueryHandler(log_meal_from_reminder, pattern="^log_meal_general_from_reminder_.*$")
        ],
        states={
            AWAIT_MEAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(cancel_pattern),
                                             await_meal_type_handler)],
            AWAIT_MEAL_INPUT: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND & ~filters.Regex(cancel_pattern),
                               await_meal_input_handler)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_meal_log_conv),
            MessageHandler(filters.Regex(cancel_pattern), cancel_meal_log_conv)
        ],
        name="meal_logging",
        persistent=True
    )


# ==================== Other Command Handlers ====================
async def log_water_command_or_button(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await (update.message or update.callback_query.message).reply_text(t("not_registered", lang))
        await start_command(update, context)
        return
    water_ref = get_water_ref(user_id)
    if water_ref:
        try:
            await asyncio.to_thread(water_ref.add, {
                'volume_ml': 250,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            message_text = t("water_logged", lang)
            if update.callback_query:
                await update.callback_query.answer(message_text)
                await update.callback_query.edit_message_text(message_text, reply_markup=None)
                await context.bot.send_message(chat_id=user_id, text=t("main_menu", lang),
                                               reply_markup=get_main_menu_keyboard(lang))
            else:
                await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard(lang))
        except Exception as e:
            logger.error(f"Error logging water for user {user_id}: {e}", exc_info=True)
            await (update.message or update.callback_query.message).reply_text(t("error_processing", lang))
    else:
        await (update.message or update.callback_query.message).reply_text(t("error_processing", lang))


async def stats_command_or_button(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)

    # Handle message or callback query
    message_obj = update.message or (update.callback_query.message if update.callback_query else None)
    if not message_obj:
        return

    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await message_obj.reply_text(t("not_registered", lang))
        await start_command(update, context)
        return

    user_data_snap = await asyncio.to_thread(user_ref.get)
    user_data = user_data_snap.to_dict() if user_data_snap.exists else {}
    user_timezone = pytz.timezone(user_data.get('timezone', 'UTC'))
    today_local = datetime.now(user_timezone).date()
    today_str = today_local.strftime('%Y-%m-%d')

    # Generate beautiful progress bars for stats
    water_goal = user_data.get('water_goal', 2000)  # Default water goal: 2000ml
    water_today = sum(user_data.get('water_log', {}).get(today_str, {}).values())

    # Water progress bar
    water_percentage = min(100, int((water_today / water_goal) * 100)) if water_goal > 0 else 0
    water_filled_blocks = int(water_percentage / 10)
    water_bar = "🟦" * water_filled_blocks + "⬜" * (10 - water_filled_blocks)

    # Calories stats if available
    calories_goal = user_data.get('calories_goal', 2000)  # Default calories goal
    food_log = user_data.get('food_log', {}).get(today_str, [])
    calories_today = sum(entry.get('calories', 0) for entry in food_log)

    # Calories progress bar
    calories_percentage = min(100, int((calories_today / calories_goal) * 100)) if calories_goal > 0 else 0
    calories_filled_blocks = int(calories_percentage / 10)
    calories_bar = "🟩" * calories_filled_blocks + "⬜" * (10 - calories_filled_blocks)

    # Create a beautiful stats message
    stats_message = f"📊 *{t('your_stats', lang)}*\n\n"

    # Water stats
    stats_message += f"💧 {t('water', lang)}: {water_today}ml / {water_goal}ml\n"
    stats_message += f"{water_bar} {water_percentage}%\n\n"

    # Calories stats
    stats_message += f"🍎 {t('calories', lang)}: {calories_today} / {calories_goal}\n"
    stats_message += f"{calories_bar} {calories_percentage}%\n\n"

    # Food entries for today
    if food_log:
        stats_message += f"🍽️ *{t('today_food', lang)}*:\n"
        for i, entry in enumerate(food_log[-3:], 1):  # Show last 3 entries
            stats_message += f"  {i}. {entry.get('name')} - {entry.get('calories')} cal\n"

        if len(food_log) > 3:
            stats_message += f"  ...and {len(food_log) - 3} more items\n"

    # Send the stats message with main menu keyboard
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            stats_message,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message_obj.reply_text(
            stats_message,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN
        )

    # Generate beautiful progress bars for stats
    water_goal = user_data.get('water_goal', 2000)  # Default water goal: 2000ml
    water_today = sum(user_data.get('water_log', {}).get(today_local.strftime('%Y-%m-%d'), {}).values())

    # Water progress bar
    water_percentage = min(100, int((water_today / water_goal) * 100))
    water_filled_blocks = int(water_percentage / 10)
    water_bar = "🟦" * water_filled_blocks + "⬜" * (10 - water_filled_blocks)

    # Calories stats if available
    calories_goal = user_data.get('calories_goal', 2000)  # Default calories goal
    calories_today = sum(entry.get('calories', 0) for entry in user_data.get('food_log', {}).get(today_local.strftime('%Y-%m-%d'), []))

    # Calories progress bar
    calories_percentage = min(100, int((calories_today / calories_goal) * 100))
    calories_filled_blocks = int(calories_percentage / 10)
    calories_bar = "🟩" * calories_filled_blocks + "⬜" * (10 - calories_filled_blocks)

    # Create a beautiful stats message
    stats_message = f"📊 *{t('your_stats', lang)}*\n\n"

    # Water stats
    stats_message += f"💧 {t('water', lang)}: {water_today}ml / {water_goal}ml\n"
    stats_message += f"{water_bar} {water_percentage}%\n\n"

    # Calories stats
    stats_message += f"🍎 {t('calories', lang)}: {calories_today} / {calories_goal}\n"
    stats_message += f"{calories_bar} {calories_percentage}%\n\n"

    # Add more stats from user data as needed
    if 'protein_goal' in user_data and 'protein_today' in user_data:
        protein_goal = user_data.get('protein_goal', 50)
        protein_today = user_data.get('protein_today', 0)
        protein_percentage = min(100, int((protein_today / protein_goal) * 100))
        protein_filled_blocks = int(protein_percentage / 10)
        protein_bar = "🟪" * protein_filled_blocks + "⬜" * (10 - protein_filled_blocks)
        stats_message += f"🥩 {t('protein', lang)}: {protein_today}g / {protein_goal}g\n"
        stats_message += f"{protein_bar} {protein_percentage}%\n"

    # Send the stats message with main menu keyboard
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            stats_message,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message_obj.reply_text(
            stats_message,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN
        )
    start_utc, end_utc = get_day_utc_boundaries(today_local, user_timezone)
    meals_ref = get_meals_ref(user_id)
    water_ref = get_water_ref(user_id)
    try:
        meals_today = []
        water_today = []
        if meals_ref:
            meals_today = list(await asyncio.to_thread(lambda: meals_ref.where('timestamp', '>=', start_utc)
                                                       .where('timestamp', '<=', end_utc).stream()))
        if water_ref:
            water_today = list(await asyncio.to_thread(lambda: water_ref.where('timestamp', '>=', start_utc)
                                                       .where('timestamp', '<=', end_utc).stream()))
        total_meals = []
        total_water = []
        if meals_ref:
            total_meals = list(await asyncio.to_thread(meals_ref.stream))
        if water_ref:
            total_water = list(await asyncio.to_thread(water_ref.stream))
        calories_today = sum(doc.to_dict().get('calories_estimated', 0) for doc in meals_today
                             if doc.to_dict().get('calories_estimated') is not None)
        water_ml_today = sum(doc.to_dict().get('volume_ml', 0) for doc in water_today
                             if doc.to_dict().get('volume_ml') is not None)
        meals_count_today = len(meals_today)
        total_water_ml = sum(doc.to_dict().get('volume_ml', 0) for doc in total_water
                             if doc.to_dict().get('volume_ml') is not None)
        total_meals_count = len(total_meals)
        # Add proper number formatting
        stats_text = t("stats_your_stats_and_goals", lang) + "\n\n"
        daily_calorie_goal = user_data.get('daily_calorie_goal')
        if daily_calorie_goal and isinstance(daily_calorie_goal, (int, float)) and daily_calorie_goal > 0:
            stats_text += f"{t('stats_daily_calorie_goal', lang)}: {int(daily_calorie_goal):,} kcal\n".replace(",", " ")
            if calories_today > 0:
                calories_remaining = max(0, daily_calorie_goal - calories_today)
                stats_text += f"{t('stats_calories_remaining', lang)}: {int(calories_remaining):,} kcal\n".replace(",",
                                                                                                                   " ")
                stats_text += f"{t('stats_calories_consumed', lang)}: {calories_today:,} kcal\n".replace(",", " ")

        # Add proper error handling for BMI calculation
        try:
            if isinstance(weight, (int, float)) and isinstance(height, (int, float)) and height > 0:
                height_m = height / 100
                bmi = weight / (height_m ** 2)
                # ... rest of BMI code ...
        except Exception as bmi_error:
            logger.warning(f"BMI calculation error: {bmi_error}")

        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML,
                                        reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Stats error: {str(e)}", exc_info=True)
        await update.message.reply_text(t("error_processing", lang) + f"\nError: {str(e)}",
                                        reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Error generating stats for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


async def help_command_or_button(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    await update.message.reply_text(t("help_text", lang), parse_mode=ParseMode.HTML,
                                    reply_markup=get_main_menu_keyboard(lang))


async def menu_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    lang = await get_user_language_db(user_id, context)
    user_ref = get_user_ref(user_id)
    if not user_ref or not (await asyncio.to_thread(user_ref.get)).exists:
        await update.message.reply_text(t("not_registered", lang))
        await start_command(update, context)
        return
    await update.message.reply_text(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))


# ==================== Error Handler ====================
async def error_handler(update: Update, context: CallbackContext) -> None:
    error_msg = f"⚠️ Error: {context.error}\n"
    if update and update.effective_message:
        error_msg += f"Last message: {update.effective_message.text}"

    logger.error(error_msg, exc_info=context.error)

    if update and (update.message or update.callback_query):
        lang = await get_user_language_db(update.effective_user.id, context)
        try:
            await (update.message or update.callback_query.message).reply_text(
                t("error_processing", lang) + "\n" + error_msg,
                reply_markup=get_main_menu_keyboard(lang)
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


# ==================== Main Bot Setup ====================
async def post_init(application: Application) -> None:
    global scheduler
    logger.info("Starting post_init...")
    commands = [
        BotCommand("start", "Start or restart the bot"),
        BotCommand("menu", "Show the main menu"),
        BotCommand("logmeal", "Log a meal"),
        BotCommand("water", "Log water intake"),
        BotCommand("stats", "View your stats and goals"),
        BotCommand("settings", "Manage settings"),
        BotCommand("help", "Get help")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set.")

    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    scheduler.add_jobstore(MemoryJobStore())
    scheduler.start()
    logger.info("APScheduler initialized and started.")

    if db:
        try:
            users_ref = db.collection('users')
            users_snap = await asyncio.to_thread(users_ref.stream)
            for user_doc in users_snap:
                user_data = user_doc.to_dict()
                user_id = int(user_doc.id)
                lang = user_data.get('language', 'en')
                timezone = user_data.get('timezone', 'UTC')
                await schedule_user_reminders_task(user_id, timezone, lang, application.bot)
            logger.info("Scheduled reminders for existing users.")
        except Exception as e:
            logger.error(f"Error scheduling reminders for existing users: {e}", exc_info=True)
    else:
        logger.warning("DB not available, cannot schedule reminders for existing users.")


def main() -> None:
    logger.info("Starting bot application...")
    persistence = PicklePersistence(filepath="bot_persistence")
    application = Application.builder().token(BOT_TOKEN).persistence(persistence).post_init(post_init).build()

    application.add_handler(registration_conversation())
    application.add_handler(settings_conversation())
    application.add_handler(meal_logging_conversation())

    application.add_handler(CommandHandler("water", log_water_command_or_button))
    application.add_handler(CallbackQueryHandler(log_water_command_or_button, pattern="^log_water_from_reminder$"))
    application.add_handler(CommandHandler("stats", stats_command_or_button))
    application.add_handler(
        MessageHandler(filters.Regex(f"^{t('menu_stats', 'en')}$|^{t('menu_stats', 'ru')}$|^{t('menu_stats', 'uz')}$"),
                       stats_command_or_button))

    application.add_handler(CommandHandler("help", help_command_or_button))
    application.add_handler(
        MessageHandler(filters.Regex(f"^{t('menu_help', 'en')}$|^{t('menu_help', 'ru')}$|^{t('menu_help', 'uz')}$"),
                       help_command_or_button))
    application.add_handler(CommandHandler("menu", menu_command))

    application.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()