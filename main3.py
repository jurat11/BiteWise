import os
import asyncio
import logging
import re
from datetime import datetime, timedelta, time
import pytz
from dotenv import load_dotenv
import traceback
from typing import Optional
import base64

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter, CommandObject
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

# Configuration
BOT_TOKEN = "8027102621:AAHcAP_XCFut_hYz0OVQZJ8jN6dTQaQkmj8"  # Replace with your actual bot token
GEMINI_API_KEY = "AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY"  # Replace with your actual Gemini API key
GOOGLE_CREDENTIALS_PATH = "./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json"  # Replace with path to your Google Cloud credentials JSON file

# Project Directory Setup
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_DIR = os.path.join(PROJECT_DIR, "credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Updated Translations with Emojis and HTML Formatting
TRANSLATIONS = {
    "intro": {
        "en": "👋 Hello! I am BiteWise. Please select your language:",
        "ru": "👋 Привет! Я BiteWise. Пожалуйста, выберите язык:",
        "uz": "👋 Salom! Men BiteWise - man. Tilni tanlang:"
    },
    "select_language": {
        "en": "Choose your language:",
        "ru": "Выберите ваш язык:",
        "uz": "Tilni tanlang:"
    },
    "food_analysis_header": {
        "en": "Nutritional Value for {food_name}:",
        "ru": "Пищевая ценность {food_name}:",
        "uz": "{food_name} uchun oziqaviy qiymat:"
    },
    "language_selected": {
        "en": "Language selected: English",
        "ru": "Язык выбран: Русский",
        "uz": "Til tanlandi: O'zbek"
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
        "ru": "Пожалуйста, введите правильный возраст от 0 до 120",
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
    "select_activity_level": {
        "en": "Select your activity level:",
        "ru": "Выберите ваш уровень активности:",
        "uz": "Faollik darajangizni tanlang:"
    },
    "activity_sedentary": {
        "en": "Sedentary (little or no exercise)",
        "ru": "Сидячий (мало или нет упражнений)",
        "uz": "Faol emas (oz yoki hech qanday mashq yo'q)"
    },
    "activity_lightly_active": {
        "en": "Lightly active (light exercise 1-3 days/week)",
        "ru": "Легкая активность (легкие упражнения 1-3 дня в неделю)",
        "uz": "Yengil faol (1-3 kun/haftada yengil mashqlar)"
    },
    "activity_moderately_active": {
        "en": "Moderately active (moderate exercise 3-5 days/week)",
        "ru": "Умеренная активность (умеренные упражнения 3-5 дней в неделю)",
        "uz": "O'rtacha faol (3-5 kun/haftada o'rtacha mashqlar)"
    },
    "activity_very_active": {
        "en": "Very active (hard exercise 6-7 days/week)",
        "ru": "Очень активный (тяжелые упражнения 6-7 дней в неделю)",
        "uz": "Juda faol (6-7 kun/haftada qattiq mashqlar)"
    },
    "activity_super_active": {
        "en": "Super active (very hard exercise, physical job)",
        "ru": "Супер активный (очень тяжелые упражнения, физическая работа)",
        "uz": "Super faol (juda qattiq mashqlar, jismoniy ish)"
    },
    "registration_complete": {
        "en": "✅ Registration complete! Welcome, {name}!",
        "ru": "✅ Регистрация завершена! Добро пожаловать, {name}!",
        "uz": "✅ Ro'yxatdan o'tish yakunlandi! Xush kelibsiz, {name}!"
    },
    "recommendation_lose_weight": {
        "en": "⚖️ To lose weight:",
        "ru": "⚖️ Чтобы похудеть:",
        "uz": "⚖️ Vazn kamaytirish uchun:"
    },
    "recommendation_gain_muscle": {
        "en": "💪 To gain muscle:",
        "ru": "💪 Чтобы набрать мышечную массу:",
        "uz": "💪 Massa oshirish uchun:"
    },
    "recommendation_eat_healthier": {
        "en": "🥗 To eat healthier:",
        "ru": "🥗 Чтобы питаться здоровее:",
        "uz": "🥗 Sog'lom ovqatlanish uchun:"
    },
    "recommendation_look_younger": {
        "en": "👶 To look younger:",
        "ru": "👶 Чтобы выглядеть моложе:",
        "uz": "👶 Yoshroq ko'rinish uchun:"
    },
    "recommendation_maintain": {
        "en": "🏋️ To maintain your weight:",
        "ru": "🏋️ Чтобы поддерживать вес:",
        "uz": "🏋️ Vazningizni saqlab qolish uchun:"
    },
    "advice_eat_healthier": {
        "en": "Focus on whole, unprocessed foods and include plenty of fruits and vegetables in your diet.",
        "ru": "Сосредоточьтесь на цельных, необработанных продуктах и включайте в рацион много фруктов и овощей.",
        "uz": "To'liq, qayta ishlanmagan ovqatlarga e'tibor bering va dietangizga ko'p meva va sabzavotlarni qo'shing."
    },
    "advice_look_younger": {
        "en": "Include foods rich in antioxidants, such as berries, nuts, and leafy greens, to support skin health.",
        "ru": "Включайте в рацион продукты, богатые антиоксидантами, такие как ягоды, орехи и зеленые листовые овощи, для поддержания здоровья кожи.",
        "uz": "Teri salomatligini qo'llab-quvvatlash uchun rezavorlar, yong'oqlar va yashil bargli sabzavotlar kabi antioksidantlarga boy ovqatlarni iste'mol qiling."
    },
    "already_registered": {
        "en": "You are already registered. Use /settings to change your preferences.",
        "ru": "Вы уже зарегистрированы. Используйте /settings для изменения настроек.",
        "uz": "Siz allaqachon ro'yxatdan o'tgansiz. Sozlamalarni o'zgartirish uchun /settings dan foydalaning."
    },
    "water_reminder": {
        "en": "💧 Time to drink water! Stay hydrated!",
        "ru": "💧 Время пить воду! Поддерживайте водный баланс!",
        "uz": "💧 Suv ichish vaqti! Suv miqdorini saqlang!"
    },
    "meal_reminder": {
        "en": "⏰ Don't forget to log your {meal_type}!",
        "ru": "⏰ Не забудьте записать свой {meal_type}!",
        "uz": "⏰ {meal_type} kiritishni unutmang!"
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
    "send_food_info_prompt": {
        "en": "Send me food info or photos to get started!",
        "ru": "Присылайте информацию о еде или фотографии, чтобы начать!",
        "uz": "Boshlash uchun ovqat haqida ma'lumot yoki rasm yuboring!"
    },
    "lose_weight": {
        "en": "Lose weight",
        "ru": "Похудеть",
        "uz": "Vazn kamaytirish"
    },
    "gain_muscle": {
        "en": "Gain muscle",
        "ru": "Набрать массу",
        "uz": "Massa oshirish"
    },
    "eat_healthier": {
        "en": "Eat healthier",
        "ru": "Питаться здоровее",
        "uz": "Sog'lom ovqat"
    },
    "daily_requirement": {
        "en": "({percentage}% of daily need)",
        "ru": "({percentage}% от дневной нормы)",
        "uz": "(kunlik ehtiyojning {percentage}%)"
    },
    "note_label": {
        "en": "Note",
        "ru": "Примечание",
        "uz": "Eslatma"
    },
    "look_younger": {
        "en": "Look younger",
        "ru": "Выглядеть моложе",
        "uz": "Yoshroq ko'rinish"
    },
    "other_goal": {
        "en": "Other goal",
        "ru": "Другая цель",
        "uz": "Boshqa maqsad"
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
    "menu_donate": {
        "en": "❤️ Support Developers",
        "ru": "❤️ Поддержать разработчиков",
        "uz": "❤️ Ishlab chiquvchilarni qo'llab-quvvatlash"
    },
    "donate_message": {
        "en": "❤️ Thank you for supporting us! Visit @bitewiseuz to help developers.",
        "ru": "❤️ Спасибо за поддержку! Посетите @bitewiseuz, чтобы помочь разработчикам.",
        "uz": "❤️ Bizni qo'llab-quvvatlaganingiz uchun rahmat! Ishlab chiquvchilarga yordam berish uchun @bitewiseuz ga tashrif buyuring."
    },
    "help_text": {
        "en": "🌟 <b>Welcome to BiteWise!</b>\n\n"
              "BiteWise is your personal nutrition assistant. It helps you track your meals and water intake, provides nutritional analysis, and offers motivational support to help you achieve your health goals.\n\n"
              "<b>Commands:</b>\n"
              "• /start - Start the bot and register\n"
              "• /menu - Show the main menu\n"
              "• /help - Show this help message\n"
              "• /water - Log water intake\n"
              "• /stats - View your statistics\n"
              "• /settings - Access settings\n"
              "• /logfood or /logmeal - Log a meal\n\n"
              "<b>How to Use:</b>\n"
              "1. <b>Log Meals:</b> Use /logfood or /logmeal or the 🍽 button to select meal type and describe your meal or send a photo.\n"
              "2. <b>Log Water:</b> Use /water or the 💧 button to log water intake.\n"
              "3. <b>View Stats:</b> Use /stats or the 📊 button to see your nutrition statistics.\n"
              "4. <b>Settings:</b> Use /settings or the ⚙️ button to change language, edit profile, or manage reminders.\n"
              "5. <b>Achievements:</b> Check your streaks and badges in Settings > My Achievements.\n"
              "6. <b>Help:</b> Use /help or the ❓ button anytime for assistance.\n\n"
              "For more assistance, contact @jurat1\n"
              "If you want to support developers, visit @BiteWiseuz ❤️",
        "ru": "🌟 <b>Добро пожаловать в BiteWise!</b>\n\n"
              "BiteWise - ваш личный помощник по питанию. Он помогает отслеживать приемы пищи и воды, предоставляет анализ питания и мотивирует вас достигать ваших целей по здоровью.\n\n"
              "<b>Команды:</b>\n"
              "• /start - Запустить бот и зарегистрироваться\n"
              "• /menu - Показать главное меню\n"
              "• /help - Показать это сообщение помощи\n"
              "• /water - Записать прием воды\n"
              "• /stats - Просмотреть статистику\n"
              "• /settings - Доступ к настройкам\n"
              "• /logfood или /logmeal - Записать прием пищи\n\n"
              "<b>Как использовать:</b>\n"
              "1. <b>Запись питания:</b> Используйте /logfood или /logmeal или кнопку 🍽, чтобы выбрать тип приема пищи и описать его или отправить фото.\n"
              "2. <b>Запись воды:</b> Используйте /water или кнопку 💧 для записи приема воды.\n"
              "3. <b>Просмотр статистики:</b> Используйте /stats или кнопку 📊 для просмотра статистики питания.\n"
              "4. <b>Настройки:</b> Используйте /settings или кнопку ⚙️ для изменения языка, редактирования профиля или управления напоминаниями.\n"
              "5. <b>Достижения:</b> Проверьте свои серии и значки в Настройки > Мои достижения.\n"
              "6. <b>Помощь:</b> Используйте /help или кнопку ❓ в любое время для получения помощи.\n\n"
              "Для дополнительной помощи или предложений обратитесь к @jurat1\n"
              "Если хотите поддержать разработчиков, посетите @BiteWiseuz ❤️",
        "uz": "🌟 <b>BiteWise ga xush kelibsiz!</b>\n\n"
              "BiteWise sizning shaxsiy ovqatlanish yordamchingiz. U ovqat va suv iste'molini kuzatish, ovqatlanish tahlilini taqdim etish va sog'lom maqsadlaringizga erishish uchun motivatsiya berishda yordam beradi.\n\n"
              "<b>Buyruqlar:</b>\n"
              "• /start - Botni ishga tushirish va ro'yxatdan o'tish\n"
              "• /menu - Asosiy menyuni ko'rsatish\n"
              "• /help - Ushbu yordam xabarini ko'rsatish\n"
              "• /water - Suv iste'molini qayd etish\n"
              "• /stats - Statistikani ko'rish\n"
              "• /settings - Sozlamalarga kirish\n"
              "• /logfood yoki /logmeal - Ovqat qayd etish\n\n"
              "<b>Qanday foydalanish:</b>\n"
              "1. <b>Ovqat qayd etish:</b> /logfood yoki /logmeal yoki 🍽 tugmasini ishlatib, ovqat turini tanlang va tasvirlang yoki rasm yuboring.\n"
              "2. <b>Suv qayd etish:</b> /water yoki 💧 tugmasini ishlatib suv iste'molini qayd eting.\n"
              "3. <b>Statistikani ko'rish:</b> /stats yoki 📊 tugmasini ishlatib ovqatlanish statistikasini ko'ring.\n"
              "4. <b>Sozlamalar:</b> /settings yoki ⚙️ tugmasini ishlatib tilni o'zgartiring, profilingizni tahrirlang yoki eslatmalarni boshqaring.\n"
              "5. <b>Yutuqlar:</b> Seriyalaringiz va nishonlaringizni Sozlamalar > Mening yutuqlarimda tekshiring.\n"
              "6. <b>Yordam:</b> Istalgan vaqtda /help yoki ❓ tugmasini ishlatib yordam oling.\n\n"
              "Qo'shimcha yordam va takliflar uchun @jurat1 ga murojaat qiling\n"
              "Agar ishlab chiquvchilarni qo'llab-quvvatlamoqchi bo'lsangiz, @BiteWiseuz ga tashrif buyuring ❤️"
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
    },
    "settings_title": {
        "en": "⚙️ Settings",
        "ru": "⚙️ Настройки",
        "uz": "⚙️ Sozlamalar"
    },
    "change_language": {
        "en": "🔤 Change Language",
        "ru": "🔤 Изменить язык",
        "uz": "🔤 Tilni o'zgartirish"
    },
    "edit_reminders": {
        "en": "⏰ Edit Reminders",
        "ru": "⏰ Редактировать напоминания",
        "uz": "⏰ Eslatmalarni tahrirlash"
    },
    "edit_profile": {
        "en": "👤 Edit Profile",
        "ru": "👤 Редактировать профиль",
        "uz": "👤 Profilni tahrirlash"
    },
    "my_achievements": {
        "en": "🏆 My Achievements",
        "ru": "🏆 Мои достижения",
        "uz": "🏆 Mening yutuqlarim"
    },
    "back_to_settings": {
        "en": "🔙 Back",
        "ru": "🔙 Назад",
        "uz": "🔙 Orqaga"
    },
    "select_new_language": {
        "en": "Select your new language:",
        "ru": "Выберите новый язык:",
        "uz": "Yangi tilni tanlang:"
    },
    "language_changed": {
        "en": "✅ Language changed successfully!",
        "ru": "✅ Язык успешно изменен!",
        "uz": "✅ Til muvaffaqiyatli o'zgartirildi!"
    },
    "edit_which_field": {
        "en": "Select field to edit:",
        "ru": "Выберите поле для редактирования:",
        "uz": "Tahrirlash uchun maydonni tanlang:"
    },
    "edit_name": {
        "en": "✏️ Name",
        "ru": "✏️ Имя",
        "uz": "✏️ Ism"
    },
    "edit_age": {
        "en": "✏️ Age",
        "ru": "✏️ Возраст",
        "uz": "✏️ Yosh"
    },
    "edit_height": {
        "en": "✏️ Height",
        "ru": "✏️ Рост",
        "uz": "✏️ Bo'y"
    },
    "edit_weight": {
        "en": "✏️ Weight",
        "ru": "✏️ Вес",
        "uz": "✏️ Vazn"
    },
    "reminder_settings": {
        "en": "⏰ Reminder Settings\n\nWater reminders: {water_status}\nMeal reminders: {meal_status}",
        "ru": "⏰ Настройки напоминаний\n\nНапоминания о воде: {water_status}\nНапоминания о еде: {meal_status}",
        "uz": "⏰ Eslatma sozlamalari\n\nSuv eslatmalari: {water_status}\nOvqat eslatmalari: {meal_status}"
    },
    "toggle_water_reminders": {
        "en": "💧 Toggle Water Reminders",
        "ru": "💧 Включить/выключить напоминания о воде",
        "uz": "💧 Suv eslatmalarini yoqish/o'chirish"
    },
    "toggle_meal_reminders": {
        "en": "🍽 Toggle Meal Reminders",
        "ru": "🍽 Включить/выключить напоминания о еде",
        "uz": "🍽 Ovqat eslatmalarini yoqish/o'chirish"
    },
    "toggle_motivational_quotes": {
        "en": "🗣 Toggle Motivational Quotes",
        "ru": "🗣 Включить/выключить мотивационные цитаты",
        "uz": "🗣 Motivatsion iboralarni yoqish/o'chirish"
    },
    "toggle_breakfast_reminder": {
        "en": "🍳 Toggle Breakfast Reminder",
        "ru": "🍳 Включить/выключить напоминание о завтраке",
        "uz": "🍳 Nonushta eslatmasini yoqish/o'chirish"
    },
    "toggle_lunch_reminder": {
        "en": "🥗 Toggle Lunch Reminder",
        "ru": "🥗 Включить/выключить напоминание об обеде",
        "uz": "🥗 Tushlik eslatmasini yoqish/o'chirish"
    },
    "toggle_dinner_reminder": {
        "en": "🍽 Toggle Dinner Reminder",
        "ru": "🍽 Включить/выключить напоминание об ужине",
        "uz": "🍽 Kechki ovqat eslatmasini yoqish/o'chirish"
    },
    "reminder_enabled": {
        "en": "✅ Enabled",
        "ru": "✅ Включены",
        "uz": "✅ Yoqilgan"
    },
    "reminder_disabled": {
        "en": "❌ Disabled",
        "ru": "❌ Выключены",
        "uz": "❌ O'chirilgan"
    },
    "enter_new_value": {
        "en": "Enter new value:",
        "ru": "Введите новое значение:",
        "uz": "Yangi qiymatni kiriting:"
    },
    "profile_updated": {
        "en": "✅ Profile updated successfully!",
        "ru": "✅ Профиль успешно обновлен!",
        "uz": "✅ Profil muvaffaqiyatli yangilandi!"
    },
    "food_analysis": {
        "en": "Food Analysis",
        "ru": "Анализ еды",
        "uz": "Ovqat tahlili"
    },
    "stats_header": {
        "en": "Your Statistics",
        "ru": "Ваша статистика",
        "uz": "Statistikangiz"
    },
    "today_summary": {
        "en": "Today's Summary",
        "ru": "Данные за текущий день",
        "uz": "Bugungi xulosa"
    },
    "water": {
        "en": "Water",
        "ru": "Вода",
        "uz": "Suv"
    },
    "meals_today": {
        "en": "Meals logged today",
        "ru": "Приемы пищи сегодня",
        "uz": "Bugun qayd etilgan ovqatlar"
    },
    "total_stats": {
        "en": "Total Stats",
        "ru": "Общая статистика",
        "uz": "Umumiy statistika"
    },
    "total_water": {
        "en": "Total Water",
        "ru": "Общее количество воды",
        "uz": "Umumiy suv"
    },
    "total_meals": {
        "en": "Total Meals Logged",
        "ru": "Всего записано приемов пищи",
        "uz": "Jami qayd etilgan ovqatlar"
    },
    "total_calories": {
        "en": "Total Calories All Time",
        "ru": "Общее количество калорий за всё время",
        "uz": "Umumiy kaloriya miqdori"
    },
    "bmi": {
        "en": "BMI",
        "ru": "ИМТ",
        "uz": "TVI"
    },
    "breakfast": {
        "en": "Breakfast",
        "ru": "Завтрак",
        "uz": "Nonushta"
    },
    "lunch": {
        "en": "Lunch",
        "ru": "Обед",
        "uz": "Tushlik"
    },
    "dinner": {
        "en": "Dinner",
        "ru": "Ужин",
        "uz": "Kechki ovqat"
    },
    "snack": {
        "en": "Snack",
        "ru": "Перекус",
        "uz": "Gazak"
    },
    "select_meal_type": {
        "en": "Select meal type:",
        "ru": "Выберите тип приема пищи:",
        "uz": "Ovqat turini tanlang:"
    },
    "describe_meal": {
        "en": "Please describe what you ate for {meal_type}:",
        "ru": "Пожалуйста, опишите, что вы ели на {meal_type}:",
        "uz": "Iltimos, {meal_type} uchun nima yeganingizni tasvirlang:"
    },
    "nutrition_terms": {
        "en": {"calories": "Calories", "protein": "Protein", "carbs": "Carbs", "fat": "Fat", "sodium": "Sodium",
               "fiber": "Fiber", "sugar": "Sugar"},
        "ru": {"calories": "Калории", "protein": "Белок", "carbs": "Углеводы", "fat": "Жиры", "sodium": "Натрий",
               "fiber": "Клетчатка", "sugar": "Сахар"},
        "uz": {"calories": "Kaloriyasi", "protein": "Oqsil", "carbs": "Uglevodlar", "fat": "Yog'lar",
               "sodium": "Natriy", "fiber": "Tola", "sugar": "Shakar"}
    },
    "disclaimer": {
        "en": "May vary slightly.",
        "ru": "Может немного отличаться.",
        "uz": "Biroz farq qilishi mumkin."
    },
    "default_motivational_quote": {
        "en": "🌟 Keep pushing towards your goals!",
        "ru": "🌟 Продолжайте двигаться к своим целям!",
        "uz": "🌟 Maqsadlaringiz sari intiling!"
    },
    "benefit": {
        "en": "Positive Effect",
        "ru": "Положительный эффект",
        "uz": "Foydali tomoni"
    },
    "streak_message": {
        "en": "🎉 You've logged {type} for {days} days in a row! Keep it up!",
        "ru": "🎉 Вы записали {type} {days} дней подряд! Продолжайте в том же духе!",
        "uz": "🎉 Siz {type} ni {days} kun davomida qayd etdingiz! Shu tarzda davom eting!"
    },
    "streak_message_water": {
        "en": "🎉 You've logged water for {days} days in a row! Keep it up!",
        "ru": "🎉 Вы записали воду {days} дней подряд! Продолжайте в том же духе!",
        "uz": "🎉 Siz suvni {days} kun davomida qayd etdingiz! Shu tarzda davom eting!"
    },
    "streak_message_meal": {
        "en": "🎉 You've logged meals for {days} days in a row! Keep it up!",
        "ru": "🎉 Вы записали приемы пищи {days} дней подряд! Продолжайте в том же духе!",
        "uz": "🎉 Siz ovqatlarni {days} kun davomida qayd etdingiz! Shu tarzda davom eting!"
    },
    "challenge_complete": {
        "en": "🏆 Congrats! You've completed the '{challenge}' challenge!",
        "ru": "🏆 Поздравляем! Вы завершили задание '{challenge}'!",
        "uz": "🏆 Tabriklaymiz! Siz '{challenge}' topshirig'ini bajardingiz!"
    },
    "badge_earned": {
        "en": "🌟 New Badge Unlocked: {badge}!",
        "ru": "🌟 Новый значок разблокирован: {badge}!",
        "uz": "🌟 Yangi nishon ochildi: {badge}!"
    },
    "badge_water_warrior": {
        "en": "Water Warrior",
        "ru": "Водный воин",
        "uz": "Suv jangchisi"
    },
    "badge_meal_master": {
        "en": "Meal Master",
        "ru": "Мастер еды",
        "uz": "Ovqat ustasi"
    },
    "weekly_summary": {
        "en": "📅 Your Weekly Summary\n\n{insights}",
        "ru": "📅 Ваша недельная сводка\n\n{insights}",
        "uz": "📅 Haftalik xulosa\n\n{insights}"
    },
    "suggest_water": {
        "en": "💧 Don't forget to log your water intake!",
        "ru": "💧 Не забудьте записать прием воды!",
        "uz": "💧 Suv ichishni qayd etishni unutmang!"
    },
    "select_body_fat_range": {
        "en": "Please select your body fat percentage range or choose an option:",
        "ru": "Пожалуйста, выберите диапазон процента жира или выберите опцию:",
        "uz": "Iltimos, yog' foizi diapazonini tanlang yoki variantni tanlang:"
    },
    "enter_custom_value": {
        "en": "Enter custom value",
        "ru": "Ввести свое значение",
        "uz": "Maxsus qiymat kiriting"
    },
    "i_dont_know": {
        "en": "I don't know",
        "ru": "Я не знаю",
        "uz": "Bilmayman"
    },
    "ask_custom_body_fat": {
        "en": "Please enter your body fat percentage (3-70%):",
        "ru": "Пожалуйста, введите ваш процент жира (3-70%):",
        "uz": "Iltimos, yog' foizingizni kiriting (3-70%):"
    },
    "new_daily_requirements": {
        "en": "New Daily Nutrition Plan",
        "ru": "Новый ежедневный план питания",
        "uz": "Yangi kunlik ovqatlanish rejasi"
    },
    "reminders_enabled_note": {
        "en": "Reminders for meals and water are enabled by default. You can manage them in settings.",
        "ru": "Напоминания о еде и воде включены по умолчанию. Вы можете управлять ими в настройках.",
        "uz": "Ovqat va suv eslatmalari sukut bo'yicha yoqilgan. Siz ularni sozlamalarda boshqarishingiz mumkin."
    },
    "cancel_action": {
        "en": "❌ Cancel",
        "ru": "❌ Отмена",
        "uz": "❌ Bekor qilish"
    },
    "action_canceled": {
        "en": "✅ Action canceled.",
        "ru": "✅ Действие отменено.",
        "uz": "✅ Harakat bekor qilindi."
    },
    "cooldown_message": {
        "en": "Please wait at least 5 minutes before logging water again.",
        "ru": "Пожалуйста, подождите не менее 5 минут перед повторной записью воды.",
        "uz": "Iltimos, suvni qayta yozishdan oldin kamida 5 daqiqa kuting."
    },
    "overhydration_warning": {
        "en": "⚠️ You are approaching your daily water intake limit. Overhydration can be a health risk.",
        "ru": "⚠️ Вы приближаетесь к дневному лимиту потребления воды. Переувлажнение может быть опасно для здоровья.",
        "uz": "⚠️ Siz kunlik suv iste'molining chegarasiga yaqinlashyapsiz. Ortiqcha suv sog'liq uchun xavfli bo'lishi mumkin."
    },
    "mute_message": {
        "en": "You have been muted for 5 minutes due to excessive water logging. Please try again later.",
        "ru": "Вы были отключены на 5 минут из-за чрезмерной записи воды. Пожалуйста, попробуйте позже.",
        "uz": "Siz suvni haddan tashqari ko'p yozganingiz uchun 5 daqiqaga o'chirildingiz. Keyinroq qayta urinib ko'ring."
    },
    "health_note": {
        "en": "Health Note",
        "ru": "Заметка о здоровье",
        "uz": "Sog'liq uchun"
    },
    "recommendation": {
        "en": "Recommendation",
        "ru": "Рекомендация",
        "uz": "Tavsiya"
    },
    "excessive_water_logging": {
        "en": "⚠️ You are logging water too frequently. Please slow down to avoid overhydration risks.",
        "ru": "⚠️ Вы слишком часто записываете воду. Замедлитесь, чтобы избежать рисков переувлажнения.",
        "uz": "⚠️ Siz suvni juda tez-tez yozmoqdasiz. Ortiqcha suv xavfidan qochish uchun sekinlashing."
    },
    "daily_requirements_set": {
        "en": "✅ Your daily nutritional requirements have been set based on your profile: {daily_calories} kcal/day.",
        "ru": "✅ Ваши ежедневные потребности в питательных веществах установлены на основе вашего профиля: {daily_calories} ккал/день.",
        "uz": "✅ Profilingiz asosida kunlik oziq-ovqat ehtiyojlaringiz belgilandi: kuniga {daily_calories} kkal."
    },
    "update_requirements": {
        "en": "✅ Your daily nutritional requirements have been updated: {daily_calories} kcal/day.",
        "ru": "✅ Ваши ежедневные потребности в питательных веществах обновлены: {daily_calories} ккал/день.",
        "uz": "✅ Kunlik oziq-ovqat ehtiyojlaringiz yangilandi: kuniga {daily_calories} kkal"
    },
    "streaks": {
        "en": "Streaks",
        "ru": "Серии",
        "uz": "Seriyalar"
    },
    "water_streak": {
        "en": "Water Streak",
        "ru": "Серия по воде",
        "uz": "Suv seriyasi"
    },
    "meal_streak": {
        "en": "Meal Streak",
        "ru": "Серия по еде",
        "uz": "Ovqat seriyasi"
    },
    "days": {
        "en": "days",
        "ru": "дней",
        "uz": "kun"
    },
    "badges": {
        "en": "Badges",
        "ru": "Значки",
        "uz": "Nishonlar"
    },
    "no_badges": {
        "en": "No badges earned yet",
        "ru": "Пока нет заработанных значков",
        "uz": "Hali nishonlar yo'q"
    },
    "yes": {
        "en": "Yes",
        "ru": "Да",
        "uz": "Ha"
    },
    "no": {
        "en": "No",
        "ru": "Нет",
        "uz": "Yo'q"
    },
    "update_weight_prompt": {
        "en": "It's Sunday! Do you want to update your weight?",
        "ru": "Сегодня воскресенье! Хотите обновить свой вес?",
        "uz": "Bugun yakshanba! Vazningizni yangilamoqchimisiz?"
    },
    "weight_update_no": {
        "en": "Okay, keep up the good work!",
        "ru": "Хорошо, продолжайте в том же духе!",
        "uz": "Yaxshi, yaxshi ishni davom ettiring!"
    },
    "enter_new_weight": {
        "en": "Please enter your new weight (kg):",
        "ru": "Пожалуйста, введите ваш новый вес (кг):",
        "uz": "Iltimos, yangi vazningizni kiriting (kg):"
    },
    "weight_loss_congrats": {
        "en": "Congratulations! You've lost {weight_lost} kg since you started. Keep it up!",
        "ru": "Поздравляем! Вы потеряли {weight_lost} кг с момента начала. Продолжайте в том же духе!",
        "uz": "Tabriklaymiz! Boshlaganingizdan beri {weight_lost} kg yo'qotdingiz. Shu tarzda davom eting!"
    },
    "weight_loss_encouragement": {
        "en": "Don't give up! Even if you haven't lost weight this week, consistency is key. Keep going!",
        "ru": "Не сдавайтесь! Даже если вы не потеряли вес на этой неделе, последовательность — ключ. Продолжайте!",
        "uz": "Taslim bo'lmang! Agar bu haftada vazn yo'qotmagan bo'lsangiz ham, doimiy bo'lish muhim. Davom eting!"
    },
    "select_water_amount": {
        "en": "Select water amount:",
        "ru": "Выберите количество воды:",
        "uz": "Suv miqdorini tanlang:"
    },
    "water_logged_amount": {
        "en": "✅ Water intake recorded! {amount}ml",
        "ru": "✅ Прием воды зарегистрирован! {amount}мл",
        "uz": "✅ Suv miqdori qayd etildi! {amount}ml"
    },
    "enter_custom_water_amount": {
        "en": "Enter custom water amount (ml):",
        "ru": "Введите количество воды (мл):",
        "uz": "Yangi suv miqdorini kiriting (ml):"
    },
    "invalid_water_amount": {
        "en": "Invalid water amount. Please enter a number between 1 and 5000.",
        "ru": "Неверное количество воды. Пожалуйста, введите число от 1 до 5000.",
        "uz": "Noto'g'ri suv miqdori. Iltimos, 1 dan 5000 gacha son kiriting."
    },
    "water_logging_cancelled": {
        "en": "Water logging cancelled.",
        "ru": "Запись воды отменена.",
        "uz": "Suv qayd etish bekor qilindi."
    },
    "ask_body_fat": {
        "en": "Please select your body fat percentage range or enter a custom value:\n\n🏃‍♂️ For Men:\n- 2-5%: Essential fat\n- 6-13%: Athletes\n- 14-17%: Fitness\n- 18-24%: Average\n- 25%+: Above average\n\n🏃‍♀️ For Women:\n- 10-13%: Essential fat\n- 14-20%: Athletes\n- 21-24%: Fitness\n- 25-31%: Average\n- 32%+: Above average\n\nYou can:\n1. Enter a specific number (3-70%)\n2. Type 'skip' if you're not sure",
        "ru": "Пожалуйста, выберите диапазон процента жира или введите точное значение:\n\n🏃‍♂️ Для мужчин:\n- 2-5%: Необходимый жир\n- 6-13%: Атлеты\n- 14-17%: Фитнес\n- 18-24%: Средний\n- 25%+: Выше среднего\n\n🏃‍♀️ Для женщин:\n- 10-13%: Необходимый жир\n- 14-20%: Атлеты\n- 21-24%: Фитнес\n- 25-31%: Средний\n- 32%+: Выше среднего\n\nВы можете:\n1. Ввести конкретное число (3-70%)\n2. Написать 'пропустить', если не уверены",
        "uz": "Yog' foizi diapazonini tanlang yoki aniq qiymatni kiriting:\n\n🏃‍♂️ Erkaklar uchun:\n- 2-5%: Zaruriy yog'\n- 6-13%: Sportchilar\n- 14-17%: Fitnes\n- 18-24%: O'rtacha\n- 25%+: O'rtachadan yuqori\n\n🏃‍♀️ Ayollar uchun:\n- 10-13%: Zaruriy yog'\n- 14-20%: Sportchilar\n- 21-24%: Fitnes\n- 25-31%: O'rtacha\n- 32%+: O'rtachadan yuqori\n\nSiz:\n1. Aniq son kiritishingiz (3-70%)\n2. Agar ishonchingiz komil bo'lmasa 'o'tkazib yuborish' deb yozishingiz mumkin"
    },
    "body_fat_ranges": {
        "en": "Body Fat Ranges",
        "ru": "Диапазоны жира",
        "uz": "Yog' diapazonlari"
    },
    "body_fat_range_3_5": {
        "en": "3-5% (Essential fat - Men)",
        "ru": "3-5% (Необходимый жир - Мужчины)",
        "uz": "3-5% (Zaruriy yog' - Erkaklar)"
    },
    "body_fat_range_6_13": {
        "en": "6-13% (Athletic - Men)",
        "ru": "6-13% (Атлетическое - Мужчины)",
        "uz": "6-13% (Sport - Erkaklar)"
    },
    "body_fat_range_14_17": {
        "en": "14-17% (Fitness - Men)",
        "ru": "14-17% (Фитнес - Мужчины)",
        "uz": "14-17% (Fitnes - Erkaklar)"
    },
    "body_fat_range_18_24": {
        "en": "18-24% (Average - Men)",
        "ru": "18-24% (Среднее - Мужчины)",
        "uz": "18-24% (O'rtacha - Erkaklar)"
    },
    "body_fat_range_25_plus_m": {
        "en": "25%+ (Above Average - Men)",
        "ru": "25%+ (Выше среднего - Мужчины)",
        "uz": "25%+ (O'rtachadan yuqori - Erkaklar)"
    },
    "body_fat_range_10_13": {
        "en": "10-13% (Essential fat - Women)",
        "ru": "10-13% (Необходимый жир - Женщины)",
        "uz": "10-13% (Zaruriy yog' - Ayollar)"
    },
    "body_fat_range_14_20": {
        "en": "14-20% (Athletic - Women)",
        "ru": "14-20% (Атлетическое - Женщины)",
        "uz": "14-20% (Sport - Ayollar)"
    },
    "body_fat_range_21_24": {
        "en": "21-24% (Fitness - Women)",
        "ru": "21-24% (Фитнес - Женщины)",
        "uz": "21-24% (Fitnes - Ayollar)"
    },
    "body_fat_range_25_31": {
        "en": "25-31% (Average - Women)",
        "ru": "25-31% (Среднее - Женщины)",
        "uz": "25-31% (O'rtacha - Ayollar)"
    },
    "body_fat_range_32_plus": {
        "en": "32%+ (Above Average - Women)",
        "ru": "32%+ (Выше среднего - Женщины)",
        "uz": "32%+ (O'rtachadan yuqori - Ayollar)"
    },
    "invalid_body_fat": {
        "en": "Invalid body fat percentage. Please enter a number between 3 and 70, or type 'skip' to skip.",
        "ru": "Неверный процент жира. Пожалуйста, введите число от 3 до 70, или напишите 'пропустить'.",
        "uz": "Noto'g'ri yog' foizi. Iltimos, 3 dan 70 gacha son kiriting yoki o'tkazib yuborish uchun 'o'tkazib yuborish' deb yozing."
    },
    "edit_body_fat": {
        "en": "Update Body Fat %",
        "ru": "Обновить % жира",
        "uz": "Yog' foizini yangilash"
    },
    "edit_reminders_text": {
        "en": "⏰ Edit Reminders\n\nWater reminders: {water_status}\nMeal reminders: {meal_status}\nMotivational quotes: {motivational_status}",
        "ru": "⏰ Редактировать напоминания\n\nНапоминания о воде: {water_status}\nНапоминания о еде: {meal_status}\nМотивационные цитаты: {motivational_status}",
        "uz": "⏰ Eslatmalarni tahrirlash\n\nSuv eslatmalari: {water_status}\nOvqat eslatmalari: {meal_status}\nMotivatsion iboralarni yoqish/o'chirish"
    },
    "enter_custom_amount": {
        "en": "Enter custom percentage",
        "ru": "Ввести точное значение",
        "uz": "Aniq qiymatni kiriting"
    },
    "food_not_recognized": {
        "en": "Food not recognized. Please try again.",
        "ru": "Еда не распознана. Пожалуйста, попробуйте еще раз.",
        "uz": "Ovqat tayyorlanmagan. Iltimos, qaytadan urinib ko'ring."
    },
    "nutrition_parse_error": {
        "en": "Failed to parse nutrition. Please try again.",
        "ru": "Не удалось распарсить данные о питании. Пожалуйста, попробуйте еще раз.",
        "uz": "Ovqat tahlilini qayta ishlashda xatolik. Iltimos, qaytadan urinib ko'ring."
    },
    "processing_food": {
        "en": "🔄 Processing your food entry...",
        "ru": "🔄 Обрабатываем ваш прием пищи...",
        "uz": "🔄 Ovqatni qayta ishlash..."
    },
    "image_processing_error": {
        "en": "Sorry, there was an error processing the image. Please try again or send text description.",
        "ru": "Извините, произошла ошибка при обработке изображения. Попробуйте еще раз или отправьте текстовое описание.",
        "uz": "Kechirasiz, rasmni qayta ishlashda xatolik yuz berdi. Qaytadan urinib ko'ring yoki matn tavsifini yuboring."
    },
    "no_food_content": {
        "en": "Please provide either a photo or text description of your meal.",
        "ru": "Пожалуйста, предоставьте фото или текстовое описание вашего приема пищи.",
        "uz": "Iltimos, ovqatingizning rasmini yoki matn tavsifini yuboring."
    },
    "meal_logged_no_nutrition": {
        "en": "Meal logged (without nutrition info)",
        "ru": "Прием пищи записан (без информации о питании)",
        "uz": "Ovqat qayd etildi (ozuqa ma'lumotisiz)"
    },
    "food_text": {
        "en": "Food description",
        "ru": "Описание еды",
        "uz": "Ovqat tavsifi"
    },
    "food_name": {
        "en": "Food name",
        "ru": "Название блюда",
        "uz": "Taom nomi"
    },
    "positive_effects": {
        "en": "Positive Effect",
        "ru": "Положительный эффект",
        "uz": "Ijobiy ta'sir"
    },
    "health_notes": {
        "en": "Health Note",
        "ru": "Примечание о здоровье",
        "uz": "Sog'liq bo'yicha eslatma"
    },
    "recommendations": {
        "en": "Recommendation",
        "ru": "Рекомендация",
        "uz": "Tavsiya"
    },
    "nutrition_note": {
        "en": "Note: Values may vary slightly",
        "ru": "Примечание: Значения могут незначительно отличаться",
        "uz": "Eslatma: Qiymatlar ozgina farq qilishi mumkin"
    },
    "nutrition_analysis_failed": {
        "en": "⚠️ Could not analyze nutritional content",
        "ru": "⚠️ Не удалось проанализировать пищевую ценность",
        "uz": "⚠️ Oziq-ovqat tarkibini tahlil qilib bo'lmadi"
    },
    "try_again_later": {
        "en": "Please try again later or provide more details about the food",
        "ru": "Пожалуйста, повторите попытку позже или предоставьте больше информации о еде",
        "uz": "Iltimos, keyinroq qayta urinib ko'ring yoki taom haqida ko'proq ma'lumot bering"
    }
}


def t(key: str, lang: str, **kwargs) -> str:
    base = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
    return base.format(**kwargs) if kwargs else base


# Initialize Services
try:
    # Set Google Cloud credentials environment variable
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH
    db = firestore.Client()
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    nutrition_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")


def get_user_ref(user_id: int):
    return db.collection('users').document(str(user_id))


def get_meals_ref(user_id: int):
    return get_user_ref(user_id).collection('meals')


def get_water_ref(user_id: int):
    return get_user_ref(user_id).collection('water')


def get_streaks_ref(user_id: int):
    return get_user_ref(user_id).collection('streaks')


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
    editing_body_fat = State()
    editing_body_fat_custom = State()


class EditRemindersStates(StatesGroup):
    main_menu = State()


class Registration(StatesGroup):
    language = State()
    name = State()
    age = State()
    height = State()
    weight = State()
    body_fat = State()  # New state
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
    waiting_for_custom_amount = State()


# Keyboard Functions
def get_language_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set_lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")]
    ])


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


def get_body_fat_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="0-5%", callback_data="bf_0_5")],
        [InlineKeyboardButton(text="5-10%", callback_data="bf_5_10")],
        [InlineKeyboardButton(text="10-15%", callback_data="bf_10_15")],
        [InlineKeyboardButton(text="15-20%", callback_data="bf_15_20")],
        [InlineKeyboardButton(text="20-25%", callback_data="bf_20_25")],
        [InlineKeyboardButton(text="25-30%", callback_data="bf_25_30")],
        [InlineKeyboardButton(text="30%+", callback_data="bf_30_plus")],
        [InlineKeyboardButton(text=t("i_dont_know", lang), callback_data="bf_unknown")],
        [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_water_amount_keyboard(lang: str):
    """Get water amount selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="250ml", callback_data="water_amount_250"),
            InlineKeyboardButton(text="500ml", callback_data="water_amount_500")
        ],
        [
            InlineKeyboardButton(text="1000ml", callback_data="water_amount_1000")
        ],
        [
            InlineKeyboardButton(text=t("enter_custom_water_amount", lang), callback_data="water_amount_custom")
        ],
        [
            InlineKeyboardButton(text=t("cancel_action", lang), callback_data="cancel_water_logging")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Define valid goals and their translations
VALID_GOALS = {
    "lose_weight": {
        "en": "⚖ Lose weight",
        "ru": "⚖ Похудеть",
        "uz": "⚖ Vazn kamaytirish"
    },
    "gain_muscle": {
        "en": "💪 Gain muscle",
        "ru": "💪 Чтобы набрать мышечную массу:",
        "uz": "💪 Massa oshirish"
    },
    "eat_healthier": {
        "en": "🥗 To eat healthier:",
        "ru": "🥗 Чтобы питаться здоровее:",
        "uz": "🥗 Sog'lom ovqat"
    },
    "look_younger": {
        "en": "👶 To look younger:",
        "ru": "👶 Чтобы выглядеть моложе:",
        "uz": "👶 Yoshroq ko'rinish uchun:"
    },
    "other_goal": {
        "en": "❓ Other goal",
        "ru": "❓ Другая цель",
        "uz": "❓ Boshqa maqsad"
    }
}


def get_goals_keyboard(lang: str):
    buttons = []
    for goal_key, translations in VALID_GOALS.items():
        text = translations[lang]
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_goal_{goal_key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_activity_level_keyboard(lang: str):
    activity_levels = [
        (t("activity_sedentary", lang), "sedentary"),
        (t("activity_lightly_active", lang), "lightly_active"),
        (t("activity_moderately_active", lang), "moderately_active"),
        (t("activity_very_active", lang), "very_active"),
        (t("activity_super_active", lang), "super_active")
    ]
    buttons = []
    for text, level in activity_levels:
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_activity_{level}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_log_meal", lang)), KeyboardButton(text=t("menu_log_water", lang))],
            [KeyboardButton(text=t("menu_stats", lang)), KeyboardButton(text=t("menu_settings", lang))],
            [KeyboardButton(text=t("menu_help", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_meal_type_keyboard(lang: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("breakfast", lang), callback_data="meal_type_breakfast"),
            InlineKeyboardButton(text=t("lunch", lang), callback_data="meal_type_lunch")
        ],
        [
            InlineKeyboardButton(text=t("dinner", lang), callback_data="meal_type_dinner"),
            InlineKeyboardButton(text=t("snack", lang), callback_data="meal_type_snack")
        ],
        [
            InlineKeyboardButton(text=t("cancel_action", lang), callback_data="cancel_meal_logging")
        ]
    ])
    return keyboard


async def get_user_language(user_id: int) -> str:
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()
    return user_data.get('language', 'en') if user_data else 'en'


async def log_water_intake(user_id: int, amount: int):
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()
    user_tz = pytz.timezone(user_data.get('timezone', 'UTC'))
    now = datetime.now(user_tz)

    water_ref = get_water_ref(user_id)
    water_ref.add({
        'amount': amount,
        'timestamp': datetime.now(pytz.utc),
        'date': now.date().isoformat()
    })

    user_ref.update({'last_active': datetime.now(pytz.utc)})


async def analyze_food(text: str, image_content: Optional[str], lang: str) -> dict:
    try:
        # If image is provided, first identify the food
        food_description = text
        if image_content:
            try:
                identify_prompt = "What food item is shown in this image? Provide a brief, specific description."
                identification = await nutrition_model.generate_content_async([identify_prompt, image_content])
                food_description = identification.text.strip()
                if not text:  # If user didn't provide text description
                    text = food_description
            except Exception as e:
                logger.error(f"Error identifying food from image: {e}")
                if not text:
                    text = "Unknown food item"

        # Now analyze the nutritional content
        prompt = f"""Analyze this food and provide nutritional information for: {text}
Please respond in this EXACT format (numbers only, no text explanations):
Calories: [number]
Protein: [number]g
Carbs: [number]g
Fat: [number]g
Sodium: [number]mg
Fiber: [number]g
Sugar: [number]g
Effect: [one short health benefit]
Note: [one short health consideration]
Tip: [one short practical tip]"""

        if image_content:
            prompt += f"\nThis is identified as: {food_description}"

        response = await nutrition_model.generate_content_async(prompt)
        content = response.text.strip()

        # Extract values using more precise regex patterns
        def extract_number(pattern, default=0):
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match and match.group(1):
                try:
                    return float(match.group(1))
                except ValueError:
                    return default
            return default

        # More specific patterns that look for numbers followed by units
        calories = extract_number(r'Calories:\s*(\d+(?:\.\d+)?)\s*(?:kcal)?')
        protein = extract_number(r'Protein:\s*(\d+(?:\.\d+)?)\s*g')
        carbs = extract_number(r'Carbs?:\s*(\d+(?:\.\d+)?)\s*g')
        fat = extract_number(r'Fat:\s*(\d+(?:\.\d+)?)\s*g')
        sodium = extract_number(r'Sodium:\s*(\d+(?:\.\d+)?)\s*mg')
        fiber = extract_number(r'Fiber:\s*(\d+(?:\.\d+)?)\s*g')
        sugar = extract_number(r'Sugar:\s*(\d+(?:\.\d+)?)\s*g')

        # Extract text fields with better handling
        def extract_text(pattern, default):
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            return match.group(1).strip() if match and match.group(1) else default

        effect = extract_text(r'Effect:\s*(.+?)(?:\n|$)', "Provides nutrients")
        note = extract_text(r'Note:\s*(.+?)(?:\n|$)', "Consider portion size")
        tip = extract_text(r'Tip:\s*(.+?)(?:\n|$)', "Enjoy as part of a balanced diet")

        # Ensure we have reasonable values
        def ensure_reasonable_value(value, min_val, max_val, default):
            try:
                value = float(value)
                if min_val <= value <= max_val:
                    return value
            except (ValueError, TypeError):
                pass
            return default

        # Apply reasonable limits to values
        calories = ensure_reasonable_value(calories, 0, 2000, 100)
        protein = ensure_reasonable_value(protein, 0, 200, 5)
        carbs = ensure_reasonable_value(carbs, 0, 200, 15)
        fat = ensure_reasonable_value(fat, 0, 200, 3)
        sodium = ensure_reasonable_value(sodium, 0, 5000, 50)
        fiber = ensure_reasonable_value(fiber, 0, 50, 2)
        sugar = ensure_reasonable_value(sugar, 0, 100, 5)

        # If all values are 0, use default values
        if calories == 0 and protein == 0 and carbs == 0 and fat == 0:
            calories = 100
            protein = 5
            carbs = 15
            fat = 3
            sodium = 50
            fiber = 2
            sugar = 5

        return {
            'name': food_description if image_content else text,
            'calories': {'amount': int(calories), 'percentage': min(int((calories / 2000) * 100), 100)},
            'protein': {'amount': round(protein, 1)},
            'carbs': {'amount': round(carbs, 1)},
            'fat': {'amount': round(fat, 1)},
            'sodium': {'amount': round(sodium, 1)},
            'fiber': {'amount': round(fiber, 1)},
            'sugar': {'amount': round(sugar, 1)},
            'positive_effects': [effect],
            'health_notes': [note],
            'recommendations': [tip],
            'analysis_successful': True
        }

    except Exception as e:
        logger.error(f"Error analyzing food: {e}")
        # Return reasonable default values instead of zeros
        return {
            'name': text or "Unknown food item",
            'calories': {'amount': 100, 'percentage': 5},
            'protein': {'amount': 5},
            'carbs': {'amount': 15},
            'fat': {'amount': 3},
            'sodium': {'amount': 50},
            'fiber': {'amount': 2},
            'sugar': {'amount': 5},
            'positive_effects': ["Provides nutrients"],
            'health_notes': ["Estimated values only"],
            'recommendations': ["Consider logging with more details for accurate analysis"],
            'analysis_successful': False
        }


def calculate_daily_requirements(user_data: dict) -> dict:
    age = user_data.get('age', 30)
    height = user_data.get('height', 170)
    weight = user_data.get('weight', 70)
    gender = user_data.get('gender', 'male')
    activity_level = user_data.get('activity_level', 'sedentary')
    body_fat = user_data.get('body_fat')

    # Basal Metabolic Rate (BMR) using Mifflin-St Jeor Equation
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Adjust BMR based on activity level
    activity_multipliers = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'super_active': 1.9
    }
    tdee = bmr * activity_multipliers.get(activity_level, 1.2)

    # Adjust for body fat if provided
    if body_fat:
        lean_body_mass = weight * (1 - body_fat / 100)
        tdee = max(tdee, lean_body_mass * 25)  # Minimum calories based on LBM

    # Macronutrient distribution (example: 40% carbs, 30% protein, 30% fat)
    daily_calories = int(tdee)
    protein_g = int(weight * 1.6)  # 1.6g per kg of body weight
    fat_g = int(daily_calories * 0.3 / 9)  # 30% of calories from fat
    carbs_g = int((daily_calories - (protein_g * 4 + fat_g * 9)) / 4)  # Remaining from carbs

    return {
        'daily_calories': daily_calories,
        'daily_protein': protein_g,
        'daily_carbs': carbs_g,
        'daily_fat': fat_g,
        'daily_water_goal': int(weight * 35),  # 35ml per kg
        'daily_sodium': 2300,
        'daily_fiber': 30,
        'daily_sugar': 50
    }


async def update_streaks_and_challenges(user_id: int, log_type: str):
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()
    user_tz = pytz.timezone(user_data.get('timezone', 'UTC'))
    today = datetime.now(user_tz).date()
    yesterday = today - timedelta(days=1)

    streaks_ref = get_streaks_ref(user_id)
    streak_doc = streaks_ref.document(log_type).get()
    streak_data = streak_doc.to_dict() if streak_doc.exists else {'count': 0, 'last_date': None}

    last_date = streak_data.get('last_date')
    if last_date:
        last_date = datetime.strptime(last_date, '%Y-%m-%d').date()

    if last_date == yesterday:
        streak_data['count'] += 1
    elif last_date != today:
        streak_data['count'] = 1

    streak_data['last_date'] = today.isoformat()
    streaks_ref.document(log_type).set(streak_data)

    lang = await get_user_language(user_id)
    if streak_data['count'] > 1:
        await bot.send_message(user_id, t(f"streak_message_{log_type}", lang, days=streak_data['count']))

    # Check for badges
    badges_ref = streaks_ref.document("badges")
    badges = badges_ref.get().to_dict() or {}

    if log_type == 'water' and streak_data['count'] >= 5 and not badges.get('water_5_days'):
        badges['water_5_days'] = True
        await bot.send_message(user_id, t("badge_earned", lang, badge=t("badge_water_warrior", lang)))
    elif log_type == 'meal':
        total_meals = len(list(get_meals_ref(user_id).get()))
        if total_meals >= 50 and not badges.get('50_meals'):
            badges['50_meals'] = True
            await bot.send_message(user_id, t("badge_earned", lang, badge=t("badge_meal_master", lang)))

    if badges:
        badges_ref.set(badges)


async def send_weekly_summary(user_id: int):
    lang = await get_user_language(user_id)
    await bot.send_message(user_id, t("weekly_summary", lang, insights="Your weekly summary goes here."))

async def send_weight_update_prompt(user_id: int):
    lang = await get_user_language(user_id)
    await bot.send_message(user_id, t("update_weight_prompt", lang))

async def schedule_default_reminders(user_id: int, timezone: str):
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()
    lang = await get_user_language(user_id)
    tz = pytz.timezone(timezone)

    scheduler.remove_all_jobs()

    if user_data.get('water_reminders_enabled', True):
        for hour in [9, 12, 15, 18, 21]:
            scheduler.add_job(
                bot.send_message,
                'cron',
                hour=hour,
                minute=0,
                timezone=tz,
                args=(user_id, t("water_reminder", lang))
            )

    if user_data.get('meal_reminders_enabled', True):
        # Set meal reminders to standard times
        meal_times = {'breakfast': (8, 30), 'lunch': (13, 0), 'dinner': (18, 0)}
        for meal_type, (hour, minute) in meal_times.items():
            scheduler.add_job(
                bot.send_message,
                'cron',
                hour=hour,
                minute=minute,
                timezone=tz,
                args=(user_id, t("meal_reminder", lang, meal_type=t(meal_type, lang)))
            )

    if user_data.get('motivational_quotes_enabled', True):
        scheduler.add_job(
            bot.send_message,
            'cron',
            hour=21,
            minute=0,
            timezone=tz,
            args=(user_id, t("default_motivational_quote", lang))
        )

    # Weekly summary every Sunday at 20:00
    scheduler.add_job(
        send_weekly_summary,
        'cron',
        day_of_week='sun',
        hour=20,
        minute=0,
        timezone=tz,
        args=(user_id,)
    )

    # Weight update prompt every Sunday at 18:00 if goal is lose_weight
    if user_data.get('goal') == 'lose_weight':
        scheduler.add_job(
            send_weight_update_prompt,
            'cron',
            day_of_week='sun',
            hour=18,
            minute=0,
            timezone=tz,
            args=(user_id,)
        )


@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()

    if user_data:
        lang = user_data.get('language', 'en')
        await message.answer(t("already_registered", lang), reply_markup=get_main_menu_keyboard(lang))
    else:
        await message.answer(t("intro", "en"), reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)


@dp.callback_query(F.data.startswith("set_lang_"), StateFilter(Registration.language))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    await state.update_data(language=lang_code)
    await callback.message.edit_text(t("ask_name", lang_code))
    await state.set_state(Registration.name)
    await callback.answer()


@dp.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    lang = (await state.get_data()).get('language', 'en')
    if 2 <= len(name) <= 50:
        await state.update_data(name=name)
        await message.answer(t("ask_age", lang))
        await state.set_state(Registration.age)
    else:
        await message.answer(t("name_error", lang))


@dp.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get('language', 'en')
    try:
        age = int(message.text.strip())
        if 0 <= age <= 120:
            await state.update_data(age=age)
            await message.answer(t("ask_height", lang))
            await state.set_state(Registration.height)
        else:
            await message.answer(t("age_error", lang))
    except ValueError:
        await message.answer(t("age_error", lang))


@dp.message(Registration.height)
async def process_height(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get('language', 'en')
    try:
        height = float(message.text.strip())
        if 50 <= height <= 250:
            await state.update_data(height=height)
            await message.answer(t("ask_weight", lang))
            await state.set_state(Registration.weight)
        else:
            await message.answer(t("height_error", lang))
    except ValueError:
        await message.answer(t("height_error", lang))


@dp.message(Registration.weight)
async def process_weight(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get('language', 'en')
    try:
        weight = float(message.text.strip())
        if 20 <= weight <= 300:
            await state.update_data(weight=weight)
            await message.answer(t("ask_body_fat", lang), reply_markup=get_body_fat_keyboard(lang))
            await state.set_state(Registration.body_fat)
        else:
            await message.answer(t("weight_error", lang))
    except ValueError:
        await message.answer(t("weight_error", lang))


@dp.callback_query(F.data.startswith("bf_"), StateFilter(Registration.body_fat))
async def process_body_fat(callback: types.CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get('language', 'en')
    bf_data = callback.data.split("_")

    if bf_data[1] == "unknown":
        await state.update_data(body_fat=None)
        await callback.message.edit_text(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))
        await state.set_state(Registration.gender)
    else:
        ranges = {
            "0_5": 2.5, "5_10": 7.5, "10_15": 12.5, "15_20": 17.5,
            "20_25": 22.5, "25_30": 27.5, "30_plus": 35
        }
        body_fat = ranges.get("_".join(bf_data[1:]))
        if body_fat:
            await state.update_data(body_fat=body_fat)
            await callback.message.edit_text(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))
            await state.set_state(Registration.gender)
        else:
            await callback.message.edit_text(t("error_processing", lang))

    await callback.answer()


@dp.message(Registration.gender)
async def process_gender(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get('language', 'en')
    gender = message.text.lower()
    if gender in [t("male", lang).lower(), t("female", lang).lower()]:
        await state.update_data(gender="male" if gender == t("male", lang).lower() else "female")
        await message.answer(t("ask_timezone", lang), reply_markup=get_timezone_keyboard())
        await state.set_state(Registration.timezone)
    else:
        await message.answer(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))


@dp.message(Registration.timezone)
async def process_timezone(message: types.Message, state: FSMContext):
    timezone = message.text.strip()
    lang = (await state.get_data()).get('language', 'en')
    try:
        pytz.timezone(timezone)
        await state.update_data(timezone=timezone)
        await message.answer(t("ask_goal", lang), reply_markup=get_goals_keyboard(lang))
        await state.set_state(Registration.goal)
    except pytz.exceptions.UnknownTimeZoneError:
        await message.answer(t("timezone_error", lang), reply_markup=get_timezone_keyboard())


@dp.callback_query(F.data.startswith("set_goal_"), StateFilter(Registration.goal))
async def process_goal(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split("_")[-1]
    lang = (await state.get_data()).get('language', 'en')
    await state.update_data(goal=goal)
    await callback.message.edit_text(t("select_activity_level", lang), reply_markup=get_activity_level_keyboard(lang))
    await state.set_state(Registration.activity_level)
    await callback.answer()


@dp.callback_query(F.data.startswith("set_activity_"), StateFilter(Registration.activity_level))
async def process_activity_level(callback: types.CallbackQuery, state: FSMContext):
    activity_level = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    data = await state.get_data()
    lang = data.get('language', 'en')

    user_data = {
        'language': data['language'],
        'name': data['name'],
        'age': data['age'],
        'height': data['height'],
        'weight': data['weight'],
        'body_fat': data.get('body_fat'),
        'gender': data['gender'],
        'timezone': data['timezone'],
        'goal': data['goal'],
        'activity_level': activity_level,
        'last_active': datetime.now(pytz.utc),
        'water_reminders_enabled': True,
        'meal_reminders_enabled': True,
        'motivational_quotes_enabled': True
    }

    requirements = calculate_daily_requirements(user_data)
    user_data.update(requirements)

    user_ref = get_user_ref(user_id)
    user_ref.set(user_data)

    await schedule_default_reminders(user_id, user_data['timezone'])

    welcome_message = (
        f"{t('registration_complete', lang, name=data['name'])}\n\n"
        f"{t('daily_requirements_set', lang, daily_calories=user_data['daily_calories'])}\n"
        f"{t('reminders_enabled_note', lang)}"
    )
    await callback.message.edit_text(welcome_message, reply_markup=get_main_menu_keyboard(lang))
    await state.clear()
    await callback.answer()


@dp.message(F.text.lower() == "📋 main menu")
@dp.message(F.text.lower() == "📋 главное меню")
@dp.message(F.text.lower() == "📋 asosiy menyu")
@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(F.text.lower() == "💧 log water")
@dp.message(F.text.lower() == "💧 записать воду")
@dp.message(F.text.lower() == "💧 suv qayd etish")
@dp.message(Command("water"))
async def log_water(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("select_water_amount", lang), reply_markup=get_water_amount_keyboard(lang))


@dp.callback_query(F.data.startswith("water_amount_"))
async def process_water_amount_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id)
    amount_str = callback.data.split("_")[-1]
    if amount_str == "custom":
        await callback.message.edit_text(t("enter_custom_water_amount", lang))
        await state.set_state(WaterLogging.waiting_for_custom_amount)
    elif amount_str == "cancel":
        await callback.message.edit_text(t("action_canceled", lang))
    else:
        try:
            amount = int(amount_str)
            await log_water_intake(callback.from_user.id, amount)
            await callback.message.edit_text(t("water_logged_amount", lang, amount=amount))
        except ValueError:
            await callback.message.edit_text(t("invalid_water_amount", lang))
    await callback.answer()


@dp.message(F.text.lower() == "📊 my stats")
@dp.message(F.text.lower() == "📊 моя статистика")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Get user data
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()
        if not user_data:
            await message.answer(t("error_processing", lang))
            return

        # Get today's date in user's timezone
        user_tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(user_tz).date()
        today_start = datetime.combine(today, time.min).replace(tzinfo=user_tz)
        today_end = datetime.combine(today, time.max).replace(tzinfo=user_tz)

        # Get water stats
        water_ref = get_water_ref(user_id)
        today_water_docs = water_ref.where('timestamp', '>=', today_start) \
            .where('timestamp', '<=', today_end).get()
        water_amount = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)
        daily_water_goal = user_data.get('daily_water_goal', 2000)
        water_percent = int((water_amount / daily_water_goal * 100)) if daily_water_goal > 0 else 0

        # Create water progress bar (cap at 10 squares)
        progress_bar_length = 10
        filled_squares = min(water_percent // 10, progress_bar_length)
        water_bar = "🟦" * filled_squares + "⬜" * (progress_bar_length - filled_squares)

        # Get all-time water stats
        all_water_docs = water_ref.get()
        total_water = sum(doc.to_dict().get('amount', 0) for doc in all_water_docs)

        # Get meal stats
        meals_ref = get_meals_ref(user_id)
        today_meals = meals_ref.where('timestamp', '>=', today_start) \
            .where('timestamp', '<=', today_end).get()
        all_meals = meals_ref.get()

        # Today's nutrition
        today_meals_list = list(today_meals)  # Convert to list once
        total_calories = sum(meal.to_dict().get('calories', 0) for meal in today_meals_list)
        total_protein = sum(meal.to_dict().get('protein', 0) for meal in today_meals_list)
        total_carbs = sum(meal.to_dict().get('carbs', 0) for meal in today_meals_list)
        total_fat = sum(meal.to_dict().get('fat', 0) for meal in today_meals_list)
        total_sodium = sum(meal.to_dict().get('sodium', 0) for meal in today_meals_list)
        total_fiber = sum(meal.to_dict().get('fiber', 0) for meal in today_meals_list)
        total_sugar = sum(meal.to_dict().get('sugar', 0) for meal in today_meals_list)

        # All-time stats
        all_meals_list = list(all_meals)
        total_meals_count = len(all_meals_list)
        all_time_calories = sum(meal.to_dict().get('calories', 0) for meal in all_meals_list)

        # Daily goals
        daily_calories = user_data.get('daily_calories', 2000)
        daily_protein = user_data.get('daily_protein', 150)
        daily_carbs = user_data.get('daily_carbs', 250)
        daily_fat = user_data.get('daily_fat', 70)
        daily_sodium = user_data.get('daily_sodium', 2300)
        daily_fiber = user_data.get('daily_fiber', 30)
        daily_sugar = user_data.get('daily_sugar', 50)

        # Calculate percentages
        calories_percent = int((total_calories / daily_calories * 100)) if daily_calories > 0 else 0
        protein_percent = int((total_protein / daily_protein * 100)) if daily_protein > 0 else 0
        carbs_percent = int((total_carbs / daily_carbs * 100)) if daily_carbs > 0 else 0
        fat_percent = int((total_fat / daily_fat * 100)) if daily_fat > 0 else 0
        sodium_percent = int((total_sodium / daily_sodium * 100)) if daily_sodium > 0 else 0
        fiber_percent = int((total_fiber / daily_fiber * 100)) if daily_fiber > 0 else 0
        sugar_percent = int((total_sugar / daily_sugar * 100)) if daily_sugar > 0 else 0

        # Calculate BMI if height and weight are available
        bmi_text = ""
        if 'height' in user_data and 'weight' in user_data:
            height_m = user_data['height'] / 100
            bmi = user_data['weight'] / (height_m * height_m)

            bmi_categories = {
                "en": {"underweight": "Underweight", "normal": "Normal weight",
                       "overweight": "Overweight", "obesity": "Obesity"},
                "ru": {"underweight": "Недостаточный вес", "normal": "Нормальный вес",
                       "overweight": "Избыточный вес", "obesity": "Ожирение"},
                "uz": {"underweight": "Vazn yetishmovchiligi", "normal": "Normal vazn",
                       "overweight": "Ortiqcha vazn", "obesity": "Semizlik"}
            }

            if bmi < 18.5:
                category = bmi_categories[lang]["underweight"]
            elif 18.5 <= bmi < 25:
                category = bmi_categories[lang]["normal"]
            elif 25 <= bmi < 30:
                category = bmi_categories[lang]["overweight"]
            else:
                category = bmi_categories[lang]["obesity"]

            bmi_text = f"\nBMI: {bmi:.1f} ({category})"

        # Build the message
        stats_message = [
            f"📊 {t('stats_header', lang)}:",
            "",
            f"{t('today_summary', lang)} ({today.strftime('%Y-%m-%d')}):",
            f"💧 {t('water', lang)}: {water_amount}ml / {daily_water_goal}ml ({water_percent}%) {water_bar}",
            f"🍽 {t('meals_today', lang)}: {len(today_meals_list)}",
            f"⚡ {t('nutrition_terms', lang)['calories']}: {total_calories}/{daily_calories} kcal ({calories_percent}%)",
            f"💪 {t('nutrition_terms', lang)['protein']}: {total_protein}g/{daily_protein}g ({protein_percent}%)",
            f"🍚 {t('nutrition_terms', lang)['carbs']}: {total_carbs}g/{daily_carbs}g ({carbs_percent}%)",
            f"🧈 {t('nutrition_terms', lang)['fat']}: {total_fat}g/{daily_fat}g ({fat_percent}%)",
            f"🧂 {t('nutrition_terms', lang)['sodium']}: {total_sodium}mg/{daily_sodium}mg ({sodium_percent}%)",
            f"🌾 {t('nutrition_terms', lang)['fiber']}: {total_fiber}g/{daily_fiber}g ({fiber_percent}%)",
            f"🍬 {t('nutrition_terms', lang)['sugar']}: {total_sugar}g/{daily_sugar}g ({sugar_percent}%)",
            "",
            f"{t('total_stats', lang)}:",
            f"💧 {t('total_water', lang)}: {total_water}ml",
            f"🍽 {t('total_meals', lang)}: {total_meals_count}",
            f"🔥 {t('total_calories', lang)}: {all_time_calories:.1f} kcal"
        ]

        if user_data.get('body_fat') is not None:
            stats_message.append(f"💪 Body Fat: {user_data['body_fat']}%")

        if bmi_text:
            stats_message.append(bmi_text)

        # Send the message
        await message.answer(
            "\n".join(stats_message),
            reply_markup=get_main_menu_keyboard(lang)
        )

    except Exception as e:
        logger.error(f"Error showing stats for user {message.from_user.id}: {e}")
        await message.answer(t("error_processing", lang))


@dp.message(F.text.lower() == "❓ help")
@dp.message(F.text.lower() == "❓ помощь")
@dp.message(F.text.lower() == "❓ yordam")
@dp.message(Command("help"))
async def show_help(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("help_text", lang))


@dp.callback_query(lambda c: c.data == "change_language")
async def change_language_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(SettingsStates.changing_language)
    await callback.message.edit_text(
        t("select_new_language", lang),
        reply_markup=get_language_inline_keyboard()
    )


@dp.callback_query(F.data.startswith("set_lang_"), StateFilter(SettingsStates.changing_language))
async def process_new_language_selection(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[-1]
    user_ref = get_user_ref(user_id)

    try:
        logger.info(f"Updating language for user {user_id} to {lang_code}")
        user_ref.update({'language': lang_code})
        updated_lang = lang_code
        await callback.message.edit_text(
            t("language_changed", updated_lang),
            reply_markup=None
        )
        await bot.send_message(
            user_id,
            t("main_menu", updated_lang),
            reply_markup=get_main_menu_keyboard(updated_lang)
        )
        logger.info(f"Language updated successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Language update error for user {user_id}: {e}")
        lang = await get_user_language(user_id)
        await callback.message.edit_text(t("error_processing", lang), reply_markup=None)

    await state.clear()
    await callback.answer()


def get_profile_edit_keyboard(lang: str, user_data: dict = None):
    """Get inline keyboard for profile editing"""
    keyboard = [
        [InlineKeyboardButton(text=t("edit_name", lang), callback_data="edit_name")],
        [InlineKeyboardButton(text=t("edit_age", lang), callback_data="edit_age")],
        [InlineKeyboardButton(text=t("edit_height", lang), callback_data="edit_height")],
        [InlineKeyboardButton(text=t("edit_weight", lang), callback_data="edit_weight")],
        [InlineKeyboardButton(text=t("edit_body_fat", lang), callback_data="edit_body_fat")]
    ]

    keyboard.append([InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.callback_query(lambda c: c.data == "edit_profile")
async def edit_profile_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        user_data = get_user_ref(user_id).get().to_dict()

        await state.set_state(EditProfileStates.selecting_field)
        await callback.message.edit_text(
            t("edit_which_field", lang),
            reply_markup=get_profile_edit_keyboard(lang, user_data)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing profile edit menu: {e}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.edit_text(t("error_processing", lang))


@dp.callback_query(EditProfileStates.selecting_field)
async def handle_profile_field_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        field = callback.data

        if field == "edit_name":
            await state.set_state(EditProfileStates.editing_name)
            await callback.message.edit_text(t("ask_name", lang))
        elif field == "edit_age":
            await state.set_state(EditProfileStates.editing_age)
            await callback.message.edit_text(t("ask_age", lang))
        elif field == "edit_height":
            await state.set_state(EditProfileStates.editing_height)
            await callback.message.edit_text(t("ask_height", lang))
        elif field == "edit_weight":
            await state.set_state(EditProfileStates.editing_weight)
            await callback.message.edit_text(t("ask_weight", lang))
        elif field == "edit_body_fat":
            await state.set_state(EditProfileStates.editing_body_fat)
            await callback.message.edit_text(
                t("select_body_fat_range", lang),
                reply_markup=get_body_fat_keyboard(lang)
            )
        elif field == "back_to_settings":
            await show_settings_callback(callback)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in profile field selection: {e}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.edit_text(t("error_processing", lang))


@dp.message(EditProfileStates.editing_name)
async def handle_new_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    new_name = message.text.strip()

    if 2 <= len(new_name) <= 50:
        get_user_ref(user_id).update({'name': new_name})
        await message.answer(
            t("profile_updated", lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
        await state.clear()
    else:
        await message.answer(t("name_error", lang))


@dp.message(EditProfileStates.editing_age)
async def handle_new_age(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        new_age = int(message.text.strip())
        if 0 <= new_age <= 120:
            user_ref = get_user_ref(user_id)
            user_ref.update({'age': new_age})
            user_data = user_ref.get().to_dict()
            requirements = calculate_daily_requirements(user_data)
            user_ref.update(requirements)
            await message.answer(
                t("profile_updated", lang),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
        else:
            await message.answer(t("age_error", lang))
    except ValueError:
        await message.answer(t("age_error", lang))


@dp.message(EditProfileStates.editing_height)
async def handle_new_height(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        new_height = float(message.text.strip())
        if 50 <= new_height <= 250:
            user_ref = get_user_ref(user_id)
            user_ref.update({'height': new_height})
            user_data = user_ref.get().to_dict()
            requirements = calculate_daily_requirements(user_data)
            user_ref.update(requirements)
            await message.answer(
                t("profile_updated", lang),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
        else:
            await message.answer(t("height_error", lang))
    except ValueError:
        await message.answer(t("height_error", lang))


@dp.message(EditProfileStates.editing_weight)
async def handle_new_weight(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        new_weight = float(message.text.strip())
        if 20 <= new_weight <= 300:
            user_ref = get_user_ref(user_id)
            user_ref.update({'weight': new_weight})
            user_data = user_ref.get().to_dict()
            requirements = calculate_daily_requirements(user_data)
            user_ref.update(requirements)
            await message.answer(
                t("profile_updated", lang),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
        else:
            await message.answer(t("weight_error", lang))
    except ValueError:
        await message.answer(t("weight_error", lang))


@dp.callback_query(F.data.startswith("bf_"), StateFilter(EditProfileStates.editing_body_fat))
async def process_body_fat_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        bf_data = callback.data.split("_")

        if len(bf_data) >= 2:
            if bf_data[1] == "unknown":
                # Handle "I don't know" selection
                user_ref = get_user_ref(user_id)
                user_ref.update({
                    'body_fat': None,
                    'last_active': datetime.now(pytz.utc)
                })
                await callback.message.edit_text(t("profile_updated", lang))
                await callback.answer()
                await state.clear()
                return

            # Extract the middle value of the range
            ranges = {
                "0_5": 2.5,
                "5_10": 7.5,
                "10_15": 12.5,
                "15_20": 17.5,
                "20_25": 22.5,
                "25_30": 27.5,
                "30_plus": 35
            }
            body_fat = ranges.get("_".join(bf_data[1:]))

            if body_fat is not None:
                # Update user data
                user_ref = get_user_ref(user_id)
                user_ref.update({
                    'body_fat': body_fat,
                    'last_active': datetime.now(pytz.utc)
                })

                # Recalculate and update requirements
                user_data = user_ref.get().to_dict()
                old_requirements = {
                    'daily_calories': user_data.get('daily_calories', 0),
                    'daily_protein': user_data.get('daily_protein', 0),
                    'daily_carbs': user_data.get('daily_carbs', 0),
                    'daily_fat': user_data.get('daily_fat', 0)
                }

                new_requirements = calculate_daily_requirements(user_data)
                user_ref.update(new_requirements)

                # Calculate changes
                changes = {
                    'calories': new_requirements['daily_calories'] - old_requirements['daily_calories'],
                    'protein': new_requirements['daily_protein'] - old_requirements['daily_protein'],
                    'carbs': new_requirements['daily_carbs'] - old_requirements['daily_carbs'],
                    'fat': new_requirements['daily_fat'] - old_requirements['daily_fat']
                }

                # Show success message with new plan and changes
                message = [
                    f"✅ {t('profile_updated', lang)}",
                    "",
                    f"💪 Body Fat: {body_fat}%",
                    "",
                    f"🎯 {t('new_daily_requirements', lang)}:",
                    f"⚡ {t('nutrition_terms', lang)['calories']}: {new_requirements['daily_calories']} kcal ({'+' if changes['calories'] > 0 else ''}{changes['calories']} kcal)",
                    f"💪 {t('nutrition_terms', lang)['protein']}: {new_requirements['daily_protein']}g ({'+' if changes['protein'] > 0 else ''}{changes['protein']}g)",
                    f"🍚 {t('nutrition_terms', lang)['carbs']}: {new_requirements['daily_carbs']}g ({'+' if changes['carbs'] > 0 else ''}{changes['carbs']}g)",
                    f"🧈 {t('nutrition_terms', lang)['fat']}: {new_requirements['daily_fat']}g ({'+' if changes['fat'] > 0 else ''}{changes['fat']}g)"
                ]

                await callback.message.edit_text("\n".join(message))
                await callback.answer()
                await state.clear()
                return

        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Error in body fat selection: {e}")
        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()


@dp.message(StateFilter(EditProfileStates.editing_body_fat_custom))
async def handle_custom_body_fat_input(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Parse body fat value
        try:
            body_fat = float(message.text.strip())
        except ValueError:
            await message.answer(t("invalid_body_fat", lang))
            return

        # Validate range
        if not (3 <= body_fat <= 70):
            await message.answer(t("invalid_body_fat", lang))
            return

        # Update user data
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()

        # Store old requirements for comparison
        old_requirements = {
            'daily_calories': user_data.get('daily_calories', 0),
            'daily_protein': user_data.get('daily_protein', 0),
            'daily_carbs': user_data.get('daily_carbs', 0),
            'daily_fat': user_data.get('daily_fat', 0)
        }

        # Update body fat
        user_data['body_fat'] = body_fat
        user_data['last_active'] = datetime.now(pytz.utc)

        # Calculate new requirements
        new_requirements = calculate_daily_requirements(user_data)

        # Update user data with new requirements
        user_data.update(new_requirements)
        user_ref.set(user_data)

        # Calculate changes
        changes = {
            'calories': new_requirements['daily_calories'] - old_requirements['daily_calories'],
            'protein': new_requirements['daily_protein'] - old_requirements['daily_protein'],
            'carbs': new_requirements['daily_carbs'] - old_requirements['daily_carbs'],
            'fat': new_requirements['daily_fat'] - old_requirements['daily_fat']
        }

        # Format message
        message_lines = [
            f"✅ {t('profile_updated', lang)}",
            "",
            f"💪 Body Fat: {body_fat}%",
            "",
            f"🎯 {t('new_daily_requirements', lang)}:",
            f"⚡ {t('nutrition_terms', lang)['calories']}: {new_requirements['daily_calories']} kcal ({'+' if changes['calories'] > 0 else ''}{changes['calories']} kcal)",
            f"💪 {t('nutrition_terms', lang)['protein']}: {new_requirements['daily_protein']}g ({'+' if changes['protein'] > 0 else ''}{changes['protein']}g)",
            f"🍚 {t('nutrition_terms', lang)['carbs']}: {new_requirements['daily_carbs']}g ({'+' if changes['carbs'] > 0 else ''}{changes['carbs']}g)",
            f"🧈 {t('nutrition_terms', lang)['fat']}: {new_requirements['daily_fat']}g ({'+' if changes['fat'] > 0 else ''}{changes['fat']}g)"
        ]

        await message.answer("\n".join(message_lines), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Error processing custom body fat: {e}")
        await message.answer(t("error_processing", lang))
        await state.clear()


@dp.callback_query(lambda c: c.data == "edit_reminders")
async def edit_reminders_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        user_data = get_user_ref(user_id).get().to_dict()

        keyboard = []
        # Water
        is_enabled = user_data.get('water_reminders_enabled', True)
        status = "✅" if is_enabled else "❌"
        text = t("toggle_water_reminders", lang)
        keyboard.append([InlineKeyboardButton(
            text=f"{text} {status}",
            callback_data="toggle_water_reminders"
        )])
        # Meal
        is_enabled = user_data.get('meal_reminders_enabled', True)
        status = "✅" if is_enabled else "❌"
        text = t("toggle_meal_reminders", lang)
        keyboard.append([InlineKeyboardButton(
            text=f"{text} {status}",
            callback_data="toggle_meal_reminders"
        )])
        # Motivational
        is_enabled = user_data.get('motivational_quotes_enabled', True)
        status = "✅" if is_enabled else "❌"
        text = t("toggle_motivational_quotes", lang)
        keyboard.append([InlineKeyboardButton(
            text=f"{text} {status}",
            callback_data="toggle_motivational_reminders"
        )])
        keyboard.append([InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")])

        await state.set_state(EditRemindersStates.main_menu)
        await callback.message.edit_text(
            t("edit_reminders_text", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reminders callback: {e}")
        await callback.message.edit_text(t("error_processing", lang))


@dp.callback_query(lambda c: c.data == "edit_body_fat")
async def edit_body_fat_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle body fat editing request"""
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)

        keyboard = [
            [
                InlineKeyboardButton(text="0-5%", callback_data="bf_0_5"),
                InlineKeyboardButton(text="5-10%", callback_data="bf_5_10"),
                InlineKeyboardButton(text="10-15%", callback_data="bf_10_15")
            ],
            [
                InlineKeyboardButton(text="15-20%", callback_data="bf_15_20"),
                InlineKeyboardButton(text="20-25%", callback_data="bf_20_25"),
                InlineKeyboardButton(text="25-30%", callback_data="bf_25_30")
            ],
            [InlineKeyboardButton(text="30%+", callback_data="bf_30_plus")],
            [InlineKeyboardButton(text=t("i_dont_know", lang), callback_data="bf_unknown")],
            [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")]
        ]

        await state.set_state(EditProfileStates.editing_body_fat)
        await callback.message.edit_text(
            text=t("select_body_fat", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in edit_body_fat_callback: {e}")
        await callback.message.edit_text(t("error_processing", lang))


@dp.callback_query(F.data.startswith("bf_"), StateFilter(EditProfileStates.editing_body_fat))
async def process_edit_body_fat_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle body fat selection"""
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        bf_data = callback.data.split("_")

        if len(bf_data) >= 2:
            if bf_data[1] == "skip":
                await callback.message.edit_text(t("profile_updated", lang))
                await callback.answer()
                await state.clear()
                return
            elif bf_data[1] == "custom":
                await callback.message.edit_text(t("ask_body_fat", lang))
                await callback.answer()
                return
            else:
                # Extract the middle value of the range
                ranges = {
                    "0_5": 2.5,
                    "5_10": 7.5,
                    "10_15": 12.5,
                    "15_20": 17.5,
                    "20_25": 22.5,
                    "25_30": 27.5,
                    "30_plus": 32.5
                }
                body_fat = ranges.get("_".join(bf_data[1:]))

                if body_fat is not None:
                    # Update user data
                    user_ref = get_user_ref(user_id)
                    user_ref.update({
                        'body_fat': body_fat,
                        'last_active': datetime.now(pytz.utc)
                    })

                    # Recalculate and update requirements
                    user_data = user_ref.get().to_dict()
                    requirements = calculate_daily_requirements(user_data)
                    user_ref.update(requirements)

                    # Show success message with new plan
                    message = (
                        f"✅ {t('profile_updated', lang)}\n\n"
                        f"💪 {t('body_fat', lang)}: {body_fat}%\n\n"
                        f"🎯 {t('new_daily_requirements', lang)}:\n"
                        f"🔸 {t('calories', lang)}: {requirements['daily_calories']} kcal\n"
                        f"🔸 {t('protein', lang)}: {requirements['daily_protein']}g\n"
                        f"🔸 {t('carbs', lang)}: {requirements['daily_carbs']}g\n"
                        f"🔸 {t('fat', lang)}: {requirements['daily_fat']}g"
                    )

                    await callback.message.edit_text(message)
                    await callback.answer()
                    await state.clear()
                    return

        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Error in body fat selection: {e}")
        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()


@dp.callback_query(F.data == "bf_custom", StateFilter(EditProfileStates.editing_body_fat))
async def process_edit_custom_body_fat_request(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        await state.set_state(EditProfileStates.editing_body_fat_custom)
        await callback.message.edit_text(t("ask_custom_body_fat", lang))
        await callback.answer()
    except Exception as e:
        logger.error(f"Error requesting custom body fat: {e}")
        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()


@dp.message(EditProfileStates.editing_body_fat_custom)
async def handle_custom_body_fat_input(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        # Parse body fat value
        try:
            body_fat = float(message.text.strip())
        except ValueError:
            await message.answer(t("invalid_body_fat", lang))
            return

        # Validate range
        if not (3 <= body_fat <= 70):
            await message.answer(t("invalid_body_fat", lang))
            return

        # Update user data
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()

        # Store old requirements for comparison
        old_requirements = {
            'daily_calories': user_data.get('daily_calories', 0),
            'daily_protein': user_data.get('daily_protein', 0),
            'daily_carbs': user_data.get('daily_carbs', 0),
            'daily_fat': user_data.get('daily_fat', 0)
        }

        # Update body fat
        user_data['body_fat'] = body_fat
        user_data['last_active'] = datetime.now(pytz.utc)

        # Calculate new requirements
        new_requirements = calculate_daily_requirements(user_data)

        # Update user data with new requirements
        user_data.update(new_requirements)
        user_ref.set(user_data)

        # Calculate changes
        changes = {
            'calories': new_requirements['daily_calories'] - old_requirements['daily_calories'],
            'protein': new_requirements['daily_protein'] - old_requirements['daily_protein'],
            'carbs': new_requirements['daily_carbs'] - old_requirements['daily_carbs'],
            'fat': new_requirements['daily_fat'] - old_requirements['daily_fat']
        }

        # Format message
        message_lines = [
            f"✅ {t('profile_updated', lang)}",
            "",
            f"💪 {t('body_fat', lang)}: {body_fat}%",
            "",
            f"🎯 {t('new_daily_requirements', lang)}:",
            f"⚡ {t('calories', lang)}: {new_requirements['daily_calories']} kcal ({'+' if changes['calories'] > 0 else ''}{changes['calories']} kcal)",
            f"💪 {t('protein', lang)}: {new_requirements['daily_protein']}g ({'+' if changes['protein'] > 0 else ''}{changes['protein']}g)",
            f"🍚 {t('carbs', lang)}: {new_requirements['daily_carbs']}g ({'+' if changes['carbs'] > 0 else ''}{changes['carbs']}g)",
            f"🧈 {t('fat', lang)}: {new_requirements['daily_fat']}g ({'+' if changes['fat'] > 0 else ''}{changes['fat']}g)"
        ]

        await message.answer("\n".join(message_lines), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Error processing custom body fat: {e}")
        await message.answer(t("error_processing", lang))
        await state.clear()


@dp.callback_query(EditRemindersStates.main_menu)
async def handle_reminder_toggle(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    action = callback.data

    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()

    if action == "toggle_water_reminders":
        current = user_data.get('water_reminders_enabled', True)
        user_ref.update({'water_reminders_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Water reminders {status}")
    elif action == "toggle_meal_reminders":
        current = user_data.get('meal_reminders_enabled', True)
        user_ref.update({'meal_reminders_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Meal reminders {status}")
    elif action == "toggle_motivational_reminders":
        current = user_data.get('motivational_quotes_enabled', True)
        user_ref.update({'motivational_quotes_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Motivational quotes {status}")
    elif action == "back_to_settings":
        await state.clear()
        await show_settings_callback(callback)
        return

    if action in ["toggle_water_reminders", "toggle_meal_reminders", "toggle_motivational_reminders"]:
        # Re-fetch user_data to get updated values
        user_data = user_ref.get().to_dict()
        await schedule_default_reminders(user_id, user_data.get('timezone', 'UTC'))
        await edit_reminders_callback(callback, state)


@dp.message(F.text.lower() == "⚙️ settings")
@dp.message(F.text.lower() == "⚙️ настройки")
@dp.message(F.text.lower() == "⚙️ sozlamalar")
@dp.message(Command("settings"))
async def show_settings(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    settings_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("change_language", lang), callback_data="change_language")],
            [InlineKeyboardButton(text=t("edit_reminders", lang), callback_data="edit_reminders")],
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="edit_profile")],
            [InlineKeyboardButton(text=t("my_achievements", lang), callback_data="my_achievements")]
        ]
    )

    await message.answer(t("settings_title", lang), reply_markup=settings_kb)


@dp.callback_query(lambda c: c.data == "back_to_settings")
async def show_settings_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    settings_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("change_language", lang), callback_data="change_language")],
            [InlineKeyboardButton(text=t("edit_reminders", lang), callback_data="edit_reminders")],
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="edit_profile")],
            [InlineKeyboardButton(text=t("my_achievements", lang), callback_data="my_achievements")]
        ]
    )

    await callback.message.edit_text(t("settings_title", lang), reply_markup=settings_kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "my_achievements")
async def show_achievements(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # Fetch streaks
    streaks_ref = get_streaks_ref(user_id)
    water_streak = streaks_ref.document("water").get().to_dict().get('count', 0) if streaks_ref.document(
        "water").get().exists else 0
    meal_streak = streaks_ref.document("meal").get().to_dict().get('count', 0) if streaks_ref.document(
        "meal").get().exists else 0

    # Fetch badges
    badges_ref = streaks_ref.document("badges").get()
    badges = badges_ref.to_dict() if badges_ref.exists else {}

    # Translate badge names
    badge_translations = {
        "water_5_days": t("badge_water_warrior", lang),
        "50_meals": t("badge_meal_master", lang)
    }

    # Build the message
    message = f"🏆 <b>{t('my_achievements', lang)}</b>\n\n"
    message += f"📈 <b>{t('streaks', lang)}:</b>\n"
    message += f"💧 {t('water_streak', lang)}: {water_streak} {t('days', lang)}\n"
    message += f"🍽 {t('meal_streak', lang)}: {meal_streak} {t('days', lang)}\n\n"

    if badges:
        message += f"🎖 <b>{t('badges', lang)}:</b>\n"
        for badge_key, earned in badges.items():
            if earned:
                badge_name = badge_translations.get(badge_key, badge_key)
                message += f"- {badge_name}\n"
    else:
        message += f"🎖 <b>{t('badges', lang)}:</b> {t('no_badges', lang)}\n"

    await callback.message.edit_text(message, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.message(F.text.lower() == "🍽 log meal")
@dp.message(F.text.lower() == "🍽 записать прием пищи")
@dp.message(F.text.lower() == "🍽 ovqat qayd etish")
@dp.message(Command("logfood"))
@dp.message(Command("logmeal"))
async def log_meal(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    try:
        await message.answer(t("select_meal_type", lang), reply_markup=get_meal_type_keyboard(lang))
        await state.set_state(MealLogging.selecting_type)
    except Exception as e:
        logger.error(f"Error in log_meal for user {user_id}: {e}")
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()


@dp.callback_query(F.data.startswith("meal_type_"), StateFilter(MealLogging.selecting_type))
async def process_meal_type_selection(callback: types.CallbackQuery, state: FSMContext):
    meal_type = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.update_data(meal_type=meal_type)
    await callback.message.edit_text(t("describe_meal", lang, meal_type=t(meal_type, lang)))
    await state.set_state(MealLogging.waiting_for_text)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_meal_logging", StateFilter(MealLogging.selecting_type))
async def cancel_meal_logging(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(t("action_canceled", lang))
    await state.clear()
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("log_meal_text_"))
async def callback_log_meal_text(callback_query: types.CallbackQuery, state: FSMContext):
    meal_type = callback_query.data.split('_')[-1]
    user_id = callback_query.from_user.id
    lang = await get_user_language(user_id)

    meal_type_translated = t(meal_type, lang)
    await callback_query.answer()
    await state.update_data(meal_type=meal_type)


# Admin broadcast functionality
# To get your ID, send a message to @userinfobot on Telegram
# It will reply with your user ID that you can add to this list
ADMIN_IDS = [5080813917]  # Add your Telegram user ID here


@dp.message(lambda m: m.text and m.text.lower().startswith("send message"))
async def broadcast_message(message: types.Message):
    """Broadcast a message to all users (admin only)"""
    try:
        # Check if user is admin and show message if not
        if message.from_user.id != 5080813917:
            await message.answer(
                "⛔️ You are not authorized to use this command.\nYour ID: " + str(message.from_user.id))
            return

        # Get the actual message content (remove "send message")
        broadcast_text = message.text[len("send message"):].strip()
        if not broadcast_text:
            await message.answer("Message content is empty")
            return

        # Send initial status
        progress_msg = await message.answer("Starting broadcast...")

        # Get all users
        all_users = list(db.collection('users').stream())
        success_count = 0
        fail_count = 0

        # Send to each user
        for user_doc in all_users:
            try:
                await bot.send_message(
                    chat_id=int(user_doc.id),
                    text=broadcast_text
                )
                success_count += 1
                # Update progress every 10 users
                if success_count % 10 == 0:
                    await progress_msg.edit_text(
                        f"Broadcasting...\nProgress: {success_count + fail_count}/{len(all_users)}\n"
                        f"Successful: {success_count}\nFailed: {fail_count}"
                    )
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user_doc.id}: {e}")
                fail_count += 1

        await progress_msg.edit_text(
            f"Broadcast completed:\nTotal users: {len(all_users)}\n"
            f"Successful: {success_count}\nFailed: {fail_count}"
        )

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await message.answer(f"Error during broadcast: {str(e)}")


@dp.callback_query(lambda c: c.data == "water_custom")
async def process_custom_water_request(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = await get_user_language(callback.from_user.id)
        await state.set_state(WaterLogging.waiting_for_custom_amount)
        await callback.message.edit_text(t("ask_water_amount", lang))
        await callback.answer()
    except Exception as e:
        logger.error(f"Error requesting custom water amount: {e}")
        await callback.message.edit_text(t("error_processing", lang))
        await state.clear()


@dp.message(WaterLogging.waiting_for_custom_amount)
async def process_custom_water_amount(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)
        amount = int(message.text.strip())

        if amount <= 0 or amount > 5000:
            await message.answer("Please enter a valid amount between 1 and 5000ml")
            return

        # Get user's timezone and log water intake
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()
        user_tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        now = datetime.now(user_tz)

        # Log water intake
        water_ref = get_water_ref(user_id)
        water_ref.add({
            'amount': amount,
            'timestamp': datetime.now(pytz.utc),
            'date': now.date().isoformat()
        })

        # Update last active
        user_ref.update({'last_active': datetime.now(pytz.utc)})

        # Simple success message
        message_text = f"✅ Water intake recorded! +{amount}ml"

        await message.answer(message_text, reply_markup=get_main_menu_keyboard(lang))
        await state.clear()

    except ValueError:
        await message.answer("Please enter a valid number between 1 and 5000ml")
    except Exception as e:
        logger.error(f"Error logging water amount: {e}")
        await message.answer(t("error_processing", lang))
        await state.clear()


@dp.message(MealLogging.waiting_for_text)
async def process_meal_text(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)
        state_data = await state.get_data()
        meal_type = state_data.get('meal_type', 'snack')
        
        # Get text and image content
        text = message.text
        image_content = None
        
        if message.photo:
            photo = message.photo[-1]  # Get the largest photo
            file = await bot.get_file(photo.file_id)
            image_bytes = await bot.download_file(file.file_path)
            image_content = base64.b64encode(image_bytes.read()).decode('utf-8')
            if not text:
                text = ""  # Allow empty text when image is provided

        if not text and not image_content:
            await message.answer(t("enter_food_description", lang))
            return

        # Show processing message
        processing_msg = await message.answer(t("processing", lang))

        try:
            now = datetime.now(pytz.utc)
            
            # Get nutrition analysis
            analysis = await analyze_food(text, image_content, lang)
            
            # Save meal data
            meal_ref = get_meals_ref(user_id).document()
            meal_data = {
                'type': meal_type,
                'text': analysis['name'],  # Use identified food name
                'timestamp': now,
                'has_image': bool(image_content),
                'calories': analysis['calories']['amount'],
                'calories_percentage': analysis['calories']['percentage'],
                'protein': analysis['protein']['amount'],
                'carbs': analysis['carbs']['amount'],
                'fat': analysis['fat']['amount'],
                'sodium': analysis['sodium']['amount'],
                'fiber': analysis['fiber']['amount'],
                'sugar': analysis['sugar']['amount']
            }

            meal_ref.set(meal_data)
            get_user_ref(user_id).update({'last_active': now})

            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass

            # Format nutrition info message
            nutrition_info = [
                f"🍽 {t('food_analysis_header', lang).format(food_name=analysis['name'])}",
                "",
                f"- Calories: {analysis['calories']['amount']} kcal ({analysis['calories']['percentage']}% of daily need) 🧮",
                f"- Protein: {analysis['protein']['amount']}g 💪",
                f"- Carbs: {analysis['carbs']['amount']}g 🍚",
                f"- Fat: {analysis['fat']['amount']}g 🧈",
                f"- Sodium: {analysis['sodium']['amount']}mg 🧂",
                f"- Fiber: {analysis['fiber']['amount']}g 🌾",
                f"- Sugar: {analysis['sugar']['amount']}g 🍬",
                ""
            ]

            if analysis['positive_effects']:
                nutrition_info.append(f"🌟 {t('positive_effects', lang)}: {analysis['positive_effects'][0]}")
            if analysis['health_notes']:
                nutrition_info.append(f"📝 {t('health_notes', lang)}: {analysis['health_notes'][0]}")
            if analysis['recommendations']:
                nutrition_info.append(f"💡 {t('recommendations', lang)}: {analysis['recommendations'][0]}")

            # Only show the analysis failed message if the analysis was not successful
            if not analysis.get('analysis_successful', False):
                nutrition_info.append("\n⚠️ " + t("nutrition_analysis_failed", lang))
                nutrition_info.append(t("try_again_later", lang))

            await message.answer("\n".join(nutrition_info))
            await update_streaks_and_challenges(user_id, "meal")
            await state.clear()

        except Exception as e:
            logger.error(f"Error analyzing food: {e}")
            await message.answer(t("nutrition_analysis_failed", lang))
            await state.clear()

    except Exception as e:
        logger.error(f"Error processing meal: {e}")
        await message.answer(t("error_processing", lang))
        await state.clear()


async def main():
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())