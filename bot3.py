import os
import asyncio
import logging
import re
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import traceback
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from google.cloud import firestore
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import io
import subprocess
import csv
import tempfile

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7189930971:AAEZ4LUYS5lLTotI4ec2W1YmS1CI3CmVmNY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCkeGBt9wgQ9R73CvmEsptK1660y89s-iY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5080813917"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "@BiteWiseBot")

# Project Directory Setup
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    "water_100ml": {"en": "100 ml", "ru": "100 мл", "uz": "100 ml"},
    "water_250ml": {"en": "250 ml", "ru": "250 мл", "uz": "250 ml"},
    "water_500ml": {"en": "500 ml", "ru": "500 мл", "uz": "500 ml"},
    "water_custom": {"en": "Custom amount", "ru": "Другое количество", "uz": "Boshqa miqdor"},
    "ask_custom_water": {"en": "Enter water amount in ml (0-5000):", "ru": "Введите количество воды в мл (0-5000):", "uz": "Suv miqdorini ml da kiriting (0-5000):"},
    "water_logged_custom": {"en": "✅ Water intake recorded! +{amount}ml", "ru": "✅ Вода записана! +{amount}мл", "uz": "✅ Suv qayd etildi! +{amount}ml"},
    "water_amount_error": {"en": "Please enter a valid amount between 0 and 5000 ml.", "ru": "Пожалуйста, введите правильное количество от 0 до 5000 мл.", "uz": "Iltimos, 0 dan 5000 ml gacha to'g'ri miqdorni kiriting."}
}


def t(key: str, lang: str, **kwargs) -> str:
    base = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
    return base.format(**kwargs) if kwargs else base


# Initialize Services
try:
    # Try to initialize Firestore with credentials if available
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
    activity_level = State()  # Added for activity level


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


def get_water_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("water_100ml", lang), callback_data="water_100")],
            [InlineKeyboardButton(text=t("water_250ml", lang), callback_data="water_250")],
            [InlineKeyboardButton(text=t("water_500ml", lang), callback_data="water_500")],
            [InlineKeyboardButton(text=t("water_custom", lang), callback_data="water_custom")],
        ]
    )


# Define valid goals and their translations
VALID_GOALS = {
    "lose_weight": {
        "en": "⚖ Lose weight",
        "ru": "⚖ Похудеть",
        "uz": "⚖ Vazn kamaytirish"
    },
    "gain_muscle": {
        "en": "💪 Gain muscle",
        "ru": "💪 Набрать массу",
        "uz": "💪 Massa oshirish"
    },
    "eat_healthier": {
        "en": "🥗 Eat healthier",
        "ru": "🥗 Питаться здоровее",
        "uz": "🥗 Sog'lom ovqat"
    },
    "look_younger": {
        "en": "👶 Look younger",
        "ru": "👶 Выглядеть моложе",
        "uz": "👶 Yoshroq ko'rinish"
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
        resize_keyboard=True
    )


def get_meal_type_keyboard(lang: str):
    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    buttons = [InlineKeyboardButton(text=t(meal_type, lang), callback_data=f"meal_type_{meal_type}") for meal_type in
               meal_types]
    cancel_button = InlineKeyboardButton(text=t("cancel_action", lang), callback_data="cancel_meal_logging")
    return InlineKeyboardMarkup(inline_keyboard=[buttons, [cancel_button]])


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


def parse_nutrition(analysis: str, lang: str) -> dict:
    nutrition = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "sodium": 0.0,
        "fiber": 0.0,
        "sugar": 0.0
    }
    terms = TRANSLATIONS["nutrition_terms"][lang]
    lines = analysis.split('\n')
    for line in lines:
        line_lower = line.lower().strip()
        for key, term in terms.items():
            if term.lower() in line_lower:
                value = re.search(r'\d+(\.\d+)?', line)
                if value:
                    nutrition[key] = float(value.group())
                    break
    return nutrition


GOAL_ADJUSTMENTS = {
    "lose_weight": -500,
    "gain_muscle": 500,
    "eat_healthier": 0,
    "look_younger": 0,
    "other_goal": 0
}

ACTIVITY_LEVELS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "super_active": 1.9
}


def calculate_daily_requirements(user_data: dict) -> dict:
    weight = user_data.get('weight', 70)
    height = user_data.get('height', 170)
    age = user_data.get('age', 30)
    gender = user_data.get('gender', 'male')
    goal = user_data.get('goal', 'maintain')
    activity_level = user_data.get('activity_level', 'sedentary')

    # Base metabolic rate calculation
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Activity multipliers with weight loss cap
    ACTIVITY_LEVELS = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "super_active": 1.9
    }

    # Apply weight loss safety cap
    if goal == "lose_weight":
        max_multiplier = 1.2
        activity_multiplier = min(
            ACTIVITY_LEVELS.get(activity_level, 1.2),
            max_multiplier
        )
    else:
        activity_multiplier = ACTIVITY_LEVELS.get(activity_level, 1.2)

    tdee = bmr * activity_multiplier

    # Goal adjustments
    GOAL_ADJUSTMENTS = {
        "lose_weight": -500,
        "gain_muscle": 500,
        "maintain": 0
    }

    daily_calories = tdee + GOAL_ADJUSTMENTS.get(goal, 0)

    # Safety minimums
    min_calories = 1500 if gender == 'male' else 1200
    daily_calories = max(daily_calories, min_calories)

    # Macronutrient ratios
    ratios = {
        "lose_weight": {"protein": 0.35, "carbs": 0.40, "fat": 0.25},
        "gain_muscle": {"protein": 0.40, "carbs": 0.40, "fat": 0.20},
        "eat_healthier": {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
        "look_younger": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
        "other_goal": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
        "maintain": {"protein": 0.25, "carbs": 0.50, "fat": 0.25}
    }

    ratio = ratios.get(goal, ratios["maintain"])

    return {
        'daily_calories': round(daily_calories),
        'daily_protein': round((daily_calories * ratio["protein"]) / 4),
        'daily_carbs': round((daily_calories * ratio["carbs"]) / 4),
        'daily_fat': round((daily_calories * ratio["fat"]) / 9),
        'activity_used': activity_multiplier  # Track actual multiplier used
    }

def get_recommendation(user_data: dict, lang: str) -> str:
    goal = user_data.get('goal', 'other_goal').lower()  # Normalize case
    daily_calories = user_data.get('daily_calories', 2000)
    protein = user_data.get('daily_protein', 50)
    carbs = user_data.get('daily_carbs', 250)
    fat = user_data.get('daily_fat', 70)

    base_message = f"⚡ {t('nutrition_terms', lang)['calories']}: {daily_calories} kcal/day\n"
    base_message += f"💪 {t('nutrition_terms', lang)['protein']}: {protein}g\n"
    base_message += f"🍚 {t('nutrition_terms', lang)['carbs']}: {carbs}g\n"
    base_message += f"🧈 {t('nutrition_terms', lang)['fat']}: {fat}g"

    if goal == "lose_weight":
        return t("recommendation_lose_weight", lang) + "\n" + base_message
    elif goal == "gain_muscle":
        return t("recommendation_gain_muscle", lang) + "\n" + base_message
    elif goal == "eat_healthier":
        return t("recommendation_eat_healthier", lang) + "\n" + base_message + "\n" + t("advice_eat_healthier", lang)
    elif goal == "look_younger":
        return t("recommendation_look_younger", lang) + "\n" + base_message + "\n" + t("advice_look_younger", lang)
    else:
        return t("recommendation_maintain", lang) + "\n" + base_message


async def update_streaks_and_challenges(user_id: int, log_type: str):
    lang = await get_user_language(user_id)
    today = datetime.now(pytz.utc).date()
    streaks_ref = get_streaks_ref(user_id)

    streak_doc = streaks_ref.document(log_type).get()
    streak_data = streak_doc.to_dict() if streak_doc.exists else {'count': 0, 'last_date': None}

    last_date = streak_data['last_date']
    if last_date:
        last_date = last_date.date()

    if last_date == today - timedelta(days=1):
        streak_data['count'] += 1
        if streak_data['count'] > 1:
            if log_type == "water":
                message_key = "streak_message_water"
            elif log_type == "meal":
                message_key = "streak_message_meal"
            else:
                message_key = "streak_message"
            await bot.send_message(user_id, t(message_key, lang, days=streak_data['count']))
    elif last_date != today:
        streak_data['count'] = 1

    streak_data['last_date'] = datetime.now(pytz.utc)
    streaks_ref.document(log_type).set(streak_data)

    badges_ref = streaks_ref.document("badges")
    badges = badges_ref.get().to_dict() or {}

    if log_type == "water" and streak_data['count'] == 5 and not badges.get("water_5_days"):
        await bot.send_message(user_id, t("challenge_complete", lang, challenge="Hit water goal 5 days"))
        badges["water_5_days"] = True
        badges_ref.set(badges)
        badge_name = t("badge_water_warrior", lang)
        await bot.send_message(user_id, t("badge_earned", lang, badge=badge_name))

    if log_type == "meal":
        total_meals = len(list(get_meals_ref(user_id).stream()))
        if total_meals >= 50 and not badges.get("50_meals"):
            badges["50_meals"] = True
            badges_ref.set(badges)
            badge_name = t("badge_meal_master", lang)
            await bot.send_message(user_id, t("badge_earned", lang, badge=badge_name))


async def _log_water_internal(user_id: int, lang: str) -> str:
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        if not user_data:
            return "error"
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        now = datetime.now(pytz.utc)
        get_water_ref(user_id).add({
            'amount': 250,
            'timestamp': now
        })
        asyncio.create_task(update_streaks_and_challenges(user_id, "water"))
        return "success"
    except Exception as e:
        logger.error(f"Error in _log_water_internal for user {user_id}: {e}")
        return "error"


# Reminder Functions
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
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("menu_log_water", lang), callback_data="log_water")]]
        )
        await bot.send_message(user_id, message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending water reminder to user {user_id}: {e}")
        if "chat not found" in str(e).lower():
            get_user_ref(user_id).update({'active': False})
            logger.info(f"Marked user {user_id} as inactive due to chat not found.")


async def send_meal_reminder(user_id: int, meal_type: str):
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        lang = user_data.get('language', 'en')
        meal_type_display = t(meal_type, lang) if meal_type in ["breakfast", "lunch", "dinner"] else meal_type
        emoji_map = {"breakfast": "🍳", "lunch": "🍲", "dinner": "🍽"}
        emoji = emoji_map.get(meal_type, "🍔")
        message = f"{emoji} {t('meal_reminder', lang, meal_type=meal_type_display)}"
        await bot.send_message(user_id, message)
    except Exception as e:
        logger.error(f"Error sending meal reminder to user {user_id}: {e}")
        if "chat not found" in str(e).lower():
            get_user_ref(user_id).update({'active': False})
            logger.info(f"Marked user {user_id} as inactive due to chat not found.")


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


async def send_weekly_summary(user_id: int):
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        lang = user_data.get('language', 'en')
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        now = datetime.now(tz)
        week_start = now - timedelta(days=now.weekday() + 1)
        week_end = week_start + timedelta(days=6)
        week_start_utc = tz.localize(datetime.combine(week_start, datetime.min.time())).astimezone(pytz.UTC)
        week_end_utc = tz.localize(datetime.combine(week_end, datetime.max.time())).astimezone(pytz.UTC)
        meals_ref = get_meals_ref(user_id)
        week_meals = list(
            meals_ref.where('timestamp', '>=', week_start_utc).where('timestamp', '<=', week_end_utc).stream())
        total_calories = sum(meal.to_dict().get('calories', 0) for meal in week_meals)
        meal_count = len(week_meals)
        water_ref = get_water_ref(user_id)
        week_water = list(
            water_ref.where('timestamp', '>=', week_start_utc).where('timestamp', '<=', week_end_utc).stream())
        total_water = sum(w.to_dict().get('amount', 0) for w in week_water)
        insights = (
            f"🍽 {t('menu_log_meal', lang)}: {meal_count}\n"
            f"🔥 {t('nutrition_terms', lang)['calories']}: {total_calories} kcal\n"
            f"💧 {t('menu_log_water', lang)}: {total_water} ml"
        )
        await bot.send_message(user_id, t("weekly_summary", lang, insights=insights))
    except Exception as e:
        logger.error(f"Error sending weekly summary to user {user_id}: {e}")


async def send_weight_update_prompt(user_id: int):
    try:
        lang = await get_user_language(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("yes", lang), callback_data="update_weight_yes")],
            [InlineKeyboardButton(text=t("no", lang), callback_data="update_weight_no")]
        ])
        await bot.send_message(user_id, t("update_weight_prompt", lang), reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending weight update prompt to user {user_id}: {e}")


# Handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    if user_ref is None:
        # Database not available, treat as new user
        await message.answer(t("intro", "en"), reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)
    elif user_ref.get().exists:
        lang = await get_user_language(user_id)
        await message.answer(t("already_registered", lang), reply_markup=get_main_menu_keyboard(lang))
    else:
        await message.answer(t("intro", "en"), reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)


@dp.callback_query(F.data.startswith("set_lang_"), StateFilter(Registration.language))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang_code = callback.data.split("_")[-1]
        user_id = callback.from_user.id
        await state.update_data(language=lang_code)
        await callback.message.edit_text(
            f"{t('language_selected', lang_code)}\n\n{t('ask_name', lang_code)}",
            reply_markup=None
        )
        await state.set_state(Registration.name)
        await callback.answer()
    except Exception as e:
        logger.error(f"Language selection error for user {callback.from_user.id}: {e}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(t("error_processing", lang))
        await state.clear()


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("help_text", lang))


@dp.message(Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
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
        if any(term.lower() in text for term in terms):
            gender = g
            break

    if not gender:
        return await message.answer(t("ask_gender", lang), reply_markup=get_gender_keyboard(lang))

    await state.update_data(gender=gender)
    await message.answer(t("ask_timezone", lang), reply_markup=get_timezone_keyboard())
    await state.set_state(Registration.timezone)


@dp.message(Registration.timezone)
async def reg_timezone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    try:
        tz = pytz.timezone(message.text.strip())
        await state.update_data(timezone=str(tz))
        await message.answer(t("ask_goal", lang), reply_markup=get_goals_keyboard(lang))
        await state.set_state(Registration.goal)
    except pytz.exceptions.UnknownTimeZoneError:
        await message.answer(t("timezone_error", lang))


# In process_goal_selection handler
@dp.callback_query(F.data.startswith("set_goal_"), StateFilter(Registration.goal))
async def process_goal_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        goal_key = callback.data.replace("set_goal_", "")
        if goal_key not in VALID_GOALS:
            raise ValueError(f"Invalid goal key: {goal_key}")

        await state.update_data(goal=goal_key)
        lang = (await state.get_data()).get("language", "en")
        await callback.message.delete()
        await bot.send_message(
            callback.from_user.id,
            t("select_activity_level", lang),
            reply_markup=get_activity_level_keyboard(lang)
        )
        await state.set_state(Registration.activity_level)
    except Exception as e:
        logger.error(f"Goal selection error: {str(e)}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(t("error_processing", lang))
        await state.clear()
    await callback.answer()

@dp.callback_query(F.data.startswith("set_activity_"), StateFilter(Registration.activity_level))
async def process_activity_level_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        activity_level = callback.data.split("_")[-1]
        user_id = callback.from_user.id
        data = await state.get_data()
        lang = data.get("language", "en")

        user_ref = get_user_ref(user_id)
        user_data = {
            **data,
            'activity_level': activity_level,
            'registered_at': datetime.now(pytz.utc),
            'telegram_username': callback.from_user.username,
            'telegram_id': user_id,
            'last_active': datetime.now(pytz.utc),
            'water_reminders': True,
            'meal_reminders': True,
            'motivational_quotes_enabled': True,
            'breakfast_reminder_enabled': True,
            'lunch_reminder_enabled': True,
            'dinner_reminder_enabled': True,
            'initial_weight': data['weight']
        }

        requirements = calculate_daily_requirements(user_data)
        user_data.update(requirements)
        user_ref.set(user_data)
        await schedule_default_reminders(user_id, data['timezone'])

        recommendation = get_recommendation(user_data, lang)
        await callback.message.delete()
        await bot.send_message(
    user_id,
    t("registration_complete", lang, name=data['name']) + "\n\n" + recommendation +
    "\n\n" + t("send_food_info_prompt", lang),
    reply_markup=get_main_menu_keyboard(lang)
)
        await state.clear()
    except Exception as e:
        logger.error(f"Activity level selection error: {str(e)}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(t("error_processing", lang))
        await state.clear()
    await callback.answer()


@dp.message(F.text.lower() == "💧 log water")
@dp.message(F.text.lower() == "💧 записать воду")
@dp.message(F.text.lower() == "💧 suv qayd etish")
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
    await message.answer(t("menu_log_water", lang), reply_markup=get_water_keyboard(lang))


@dp.callback_query(lambda c: c.data in ["water_100", "water_250", "water_500", "water_custom"])
async def handle_water_option(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    if callback.data == "water_custom":
        await callback.message.answer(t("ask_custom_water", lang))
        await state.set_state(WaterLogging.waiting_for_custom)
    else:
        amount = int(callback.data.split("_")[1])
        now = datetime.now(pytz.utc)
        # Log water if database is available
        water_ref = get_water_ref(user_id)
        if water_ref is not None:
            try:
                water_ref.add({'amount': amount, 'timestamp': now})
                asyncio.create_task(update_streaks_and_challenges(user_id, "water"))
            except Exception as e:
                logger.warning(f"Failed to log water for user {user_id}: {e}")
        await callback.message.answer(t("water_logged_custom", lang, amount=amount), reply_markup=get_main_menu_keyboard(lang))
        await callback.answer()


@dp.message(WaterLogging.waiting_for_custom)
async def handle_custom_water(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    try:
        amount = int(message.text.strip())
        if not (0 < amount <= 5000):
            raise ValueError
        now = datetime.now(pytz.utc)
        # Log water if database is available
        water_ref = get_water_ref(user_id)
        if water_ref is not None:
            try:
                water_ref.add({'amount': amount, 'timestamp': now})
                asyncio.create_task(update_streaks_and_challenges(user_id, "water"))
            except Exception as e:
                logger.warning(f"Failed to log custom water for user {user_id}: {e}")
        await message.answer(t("water_logged_custom", lang, amount=amount), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()
    except Exception:
        await message.answer(t("water_amount_error", lang))


@dp.message(F.text.lower() == "📊 my stats")
@dp.message(F.text.lower() == "📊 моя статистика")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(F.text.lower() == "📊 mening statistikam")
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)

        get_user_ref(user_id).update({'last_active': datetime.now(pytz.utc)})
        await message.answer(t("processing", lang))

        user_data = get_user_ref(user_id).get().to_dict()
        if not user_data:
            return await message.answer(t("error_processing", lang) + " User data not found.",
                                        reply_markup=get_main_menu_keyboard(lang))

        if 'daily_calories' not in user_data:
            requirements = calculate_daily_requirements(user_data)
            get_user_ref(user_id).update(requirements)
            user_data.update(requirements)

        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(tz).date()
        today_start = tz.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
        today_end = tz.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)

        water_ref = get_water_ref(user_id)
        today_water_docs = list(
            water_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_water = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)
        total_water = sum(doc.to_dict().get('amount', 0) for doc in water_ref.stream())

        meals_ref = get_meals_ref(user_id)
        today_meal_docs = list(
            meals_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_meals = len(today_meal_docs)
        today_calories = sum(m.to_dict().get('calories', 0) for m in today_meal_docs)
        today_protein = sum(m.to_dict().get('protein', 0) for m in today_meal_docs)
        today_carbs = sum(m.to_dict().get('carbs', 0) for m in today_meal_docs)
        today_fat = sum(m.to_dict().get('fat', 0) for m in today_meal_docs)
        today_sodium = sum(m.to_dict().get('sodium', 0) for m in today_meal_docs)
        today_fiber = sum(m.to_dict().get('fiber', 0) for m in today_meal_docs)
        today_sugar = sum(m.to_dict().get('sugar', 0) for m in today_meal_docs)

        all_meal_docs = list(meals_ref.stream())
        total_meals = len(all_meal_docs)
        total_calories = sum(m.to_dict().get('calories', 0) for m in all_meal_docs)

        daily_calories = user_data.get('daily_calories', 2000)
        daily_protein = user_data.get('daily_protein', 50)
        daily_carbs = user_data.get('daily_carbs', 250)
        daily_fat = user_data.get('daily_fat', 70)
        daily_sodium = user_data.get('daily_sodium', 2300)
        daily_fiber = user_data.get('daily_fiber', 30)
        daily_sugar = user_data.get('daily_sugar', 50)

        # Calculate water goal and progress
        daily_water_goal = int(user_data['weight'] * 35)
        water_percent = int((today_water / daily_water_goal) * 100) if daily_water_goal > 0 else 0
        progress_bar_length = 10
        water_bar = "🟦" * min(int((today_water / daily_water_goal) * progress_bar_length),
                              progress_bar_length) + "⬜" * (
                            progress_bar_length - min(int((today_water / daily_water_goal) * progress_bar_length),
                                                      progress_bar_length))

        # Calculate percentages for nutritional values (capped at 100% for consistency)
        calories_percent = min(int((today_calories / daily_calories) * 100), 100) if daily_calories > 0 else 0
        protein_percent = min(int((today_protein / daily_protein) * 100), 100) if daily_protein > 0 else 0
        carbs_percent = min(int((today_carbs / daily_carbs) * 100), 100) if daily_carbs > 0 else 0
        fat_percent = min(int((today_fat / daily_fat) * 100), 100) if daily_fat > 0 else 0
        sodium_percent = min(int((today_sodium / daily_sodium) * 100), 100) if daily_sodium > 0 else 0
        fiber_percent = min(int((today_fiber / daily_fiber) * 100), 100) if daily_fiber > 0 else 0
        sugar_percent = min(int((today_sugar / daily_sugar) * 100), 100) if daily_sugar > 0 else 0

        terms = TRANSLATIONS["nutrition_terms"][lang]
        response = (
            f"📊 <b>{t('stats_header', lang)}:</b>\n\n"
            f"<b>{t('today_summary', lang)} ({today.strftime('%Y-%m-%d')}):</b>\n"
            f"💧 <b>{t('water', lang)}:</b> {today_water}ml / {daily_water_goal}ml ({water_percent}%) {water_bar}\n"
            f"🍽 <b>{t('meals_today', lang)}:</b> {today_meals}\n"
            f"⚡ <b>{terms['calories']}:</b> {today_calories} kcal ({calories_percent}%)\n"
            f"💪 <b>{terms['protein']}:</b> {today_protein}g ({protein_percent}%)\n"
            f"🍚 <b>{terms['carbs']}:</b> {today_carbs}g ({carbs_percent}%)\n"
            f"🧈 <b>{terms['fat']}:</b> {today_fat}g ({fat_percent}%)\n"
            f"🧂 <b>{terms['sodium']}:</b> {today_sodium}mg ({sodium_percent}%)\n"
            f"🌾 <b>{terms['fiber']}:</b> {today_fiber}g ({fiber_percent}%)\n"
            f"🍬 <b>{terms['sugar']}:</b> {today_sugar}g ({sugar_percent}%)\n\n"
            f"<b>{t('total_stats', lang)}:</b>\n"
            f"💧 <b>{t('total_water', lang)}:</b> {total_water}ml\n"
            f"🍽 <b>{t('total_meals', lang)}:</b> {total_meals}\n"
            f"🔥 <b>{t('total_calories', lang)}:</b> {total_calories} kcal\n"
        )

        if 'height' in user_data and 'weight' in user_data:
            height_m = user_data['height'] / 100
            bmi = user_data['weight'] / (height_m * height_m)
            bmi_categories = {
                "en": {"underweight": "Underweight", "normal": "Normal weight", "overweight": "Overweight",
                       "obesity": "Obesity"},
                "ru": {"underweight": "Недостаточный вес", "normal": "Нормальный вес", "overweight": "Избыточный вес",
                       "obesity": "Ожирение"},
                "uz": {"underweight": "Vazn yetishmovchiligi", "normal": "Normal vazn", "overweight": "Ortiqcha vazn",
                       "obesity": "Semizlik"}
            }
            category = "normal"
            if bmi < 18.5:
                category = bmi_categories[lang]["underweight"]
            elif 18.5 <= bmi < 25:
                category = bmi_categories[lang]["normal"]
            elif 25 <= bmi < 30:
                category = bmi_categories[lang]["overweight"]
            else:
                category = bmi_categories[lang]["obesity"]
            response += f"\n<b>{t('bmi', lang)}:</b> {bmi:.1f} ({category})"

        await message.answer(response, reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Stats error for user {message.from_user.id}: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))


@dp.message(F.text.lower() == "❓ help")
@dp.message(F.text.lower() == "❓ помощь")
@dp.message(F.text.lower() == "❓ yordam")
async def show_help(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await message.answer(t("help_text", lang), reply_markup=get_main_menu_keyboard(lang))


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


@dp.callback_query(lambda c: c.data == "edit_profile")
async def edit_profile_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("edit_name", lang), callback_data="edit_name")],
        [InlineKeyboardButton(text=t("edit_age", lang), callback_data="edit_age")],
        [InlineKeyboardButton(text=t("edit_height", lang), callback_data="edit_height")],
        [InlineKeyboardButton(text=t("edit_weight", lang), callback_data="edit_weight")],
        [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")]
    ])

    await callback.message.edit_text(
        t("edit_which_field", lang),
        reply_markup=keyboard
    )
    await state.set_state(EditProfileStates.selecting_field)
    await callback.answer()


@dp.callback_query(EditProfileStates.selecting_field)
async def handle_profile_field_selection(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    field = callback.data

    if field == "edit_name":
        await state.set_state(EditProfileStates.editing_name)
        await callback.message.answer(t("enter_new_value", lang))
    elif field == "edit_age":
        await state.set_state(EditProfileStates.editing_age)
        await callback.message.answer(t("enter_new_value", lang))
    elif field == "edit_height":
        await state.set_state(EditProfileStates.editing_height)
        await callback.message.answer(t("enter_new_value", lang))
    elif field == "edit_weight":
        await state.set_state(EditProfileStates.editing_weight)
        await callback.message.answer(t("enter_new_value", lang))
    elif field == "back_to_settings":
        await state.clear()
        await show_settings_callback(callback)

    await callback.answer()


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


@dp.callback_query(lambda c: c.data == "edit_reminders")
async def edit_reminders_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_data = get_user_ref(user_id).get().to_dict()

    water_status = t("reminder_enabled" if user_data.get('water_reminders', True) else "reminder_disabled", lang)
    meal_status = t("reminder_enabled" if user_data.get('meal_reminders', True) else "reminder_disabled", lang)
    motivation_status = t(
        "reminder_enabled" if user_data.get('motivational_quotes_enabled', True) else "reminder_disabled", lang)
    breakfast_status = t(
        "reminder_enabled" if user_data.get('breakfast_reminder_enabled', True) else "reminder_disabled", lang)
    lunch_status = t("reminder_enabled" if user_data.get('lunch_reminder_enabled', True) else "reminder_disabled", lang)
    dinner_status = t("reminder_enabled" if user_data.get('dinner_reminder_enabled', True) else "reminder_disabled",
                      lang)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t('toggle_water_reminders', lang)} ({water_status})",
                              callback_data="toggle_water")],
        [InlineKeyboardButton(text=f"{t('toggle_meal_reminders', lang)} ({meal_status})", callback_data="toggle_meal")],
        [InlineKeyboardButton(text=f"{t('toggle_motivational_quotes', lang)} ({motivation_status})",
                              callback_data="toggle_motivation")],
        [InlineKeyboardButton(text=f"{t('toggle_breakfast_reminder', lang)} ({breakfast_status})",
                              callback_data="toggle_breakfast")],
        [InlineKeyboardButton(text=f"{t('toggle_lunch_reminder', lang)} ({lunch_status})",
                              callback_data="toggle_lunch")],
        [InlineKeyboardButton(text=f"{t('toggle_dinner_reminder', lang)} ({dinner_status})",
                              callback_data="toggle_dinner")],
        [InlineKeyboardButton(text=t("back_to_settings", lang), callback_data="back_to_settings")]
    ])

    await callback.message.edit_text(
        t("reminder_settings", lang).format(water_status=water_status, meal_status=meal_status),
        reply_markup=keyboard
    )
    await state.set_state(EditRemindersStates.main_menu)


@dp.callback_query(EditRemindersStates.main_menu)
async def handle_reminder_toggle(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    action = callback.data

    user_ref = get_user_ref(user_id)
    user_data = user_ref.get().to_dict()

    if action == "toggle_water":
        current = user_data.get('water_reminders', True)
        user_ref.update({'water_reminders': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Water reminders {status}")
    elif action == "toggle_meal":
        current = user_data.get('meal_reminders', True)
        user_ref.update({'meal_reminders': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Meal reminders {status}")
    elif action == "toggle_motivation":
        current = user_data.get('motivational_quotes_enabled', True)
        user_ref.update({'motivational_quotes_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Motivational quotes {status}")
    elif action == "toggle_breakfast":
        current = user_data.get('breakfast_reminder_enabled', True)
        user_ref.update({'breakfast_reminder_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Breakfast reminder {status}")
    elif action == "toggle_lunch":
        current = user_data.get('lunch_reminder_enabled', True)
        user_ref.update({'lunch_reminder_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Lunch reminder {status}")
    elif action == "toggle_dinner":
        current = user_data.get('dinner_reminder_enabled', True)
        user_ref.update({'dinner_reminder_enabled': not current})
        status = t("reminder_disabled" if current else "reminder_enabled", lang)
        await callback.answer(f"Dinner reminder {status}")
    elif action == "back_to_settings":
        await state.clear()
        await show_settings_callback(callback)

    if action in ["toggle_water", "toggle_meal", "toggle_motivation", "toggle_breakfast", "toggle_lunch",
                  "toggle_dinner"]:
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
    await state.set_state(MealLogging.waiting_for_text)
    await bot.send_message(
        user_id,
        t("describe_meal", lang).format(meal_type=meal_type_translated),
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(MealLogging.waiting_for_text, F.photo)
async def handle_photo_in_text_state(message: types.Message, state: FSMContext):
    await handle_photo(message, state)

async def handle_photo(message: types.Message, state: FSMContext = None):
    processing_msg = None
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        logger.info(f"Starting photo processing for user {user_id}")
        get_user_ref(user_id).update({'last_active': datetime.now(pytz.utc)})
        processing_msg = await message.answer(t("processing", lang))

        photo = message.photo[-1]
        logger.info(f"Photo file_id for user {user_id}: {photo.file_id}")
        file = await bot.get_file(photo.file_id)
        file_io = io.BytesIO()
        await bot.download_file(file.file_path, file_io)
        file_io.seek(0)

        data = await state.get_data() if state else {}
        meal_type = data.get('meal_type', 'meal')

        language_names = {'en': 'English', 'ru': 'Russian', 'uz': 'Uzbek'}
        language = language_names.get(lang, 'English')
        terms = TRANSLATIONS["nutrition_terms"][lang]
        disclaimer = t("disclaimer", lang)
        benefit = t("benefit", lang)
        health_note = t("health_note", lang)
        recommendation = t("recommendation", lang)

        logger.info(f"Uploading photo to Gemini for user {user_id}")
        uploaded_file = genai.upload_file(file_io, mime_type="image/jpeg")
        user_data = get_user_ref(user_id).get().to_dict()
        daily_calories = user_data.get('daily_calories', 2000)
        prompt = f"In {language}, analyze this food image, identify the food item, and provide nutritional information for a typical serving in the following format:\n\n"
        prompt += f"{t('food_analysis_header', lang, food_name='[Identified food name]')}:\n\n"
        prompt += f"- {terms['calories']}: [value] kcal {t('daily_requirement', lang, percentage='[percentage]')} 🧮\n"
        prompt += f"- {terms['protein']}: [value]g 💪\n"
        prompt += f"- {terms['carbs']}: [value]g 🍚\n"
        prompt += f"- {terms['fat']}: [value]g 🧈\n"
        prompt += f"- {terms['sodium']}: [value]mg 🧂\n"
        prompt += f"- {terms['fiber']}: [value]g 🌾\n"
        prompt += f"- {terms['sugar']}: [value]g 🍬\n\n"
        prompt += f"🌟 {benefit}: [short positive effect]\n"
        prompt += f"🩺 {health_note}: [health note]\n"
        prompt += f"💡 {recommendation}: [recommendation]\n"
        prompt += f"⚠️ {t('note_label', lang)}: {disclaimer}\n\n"
        prompt += f"Use {daily_calories} kcal as the daily calorie need for percentage calculation. If the food is not recognized, suggest a similar common food item.\n"
        prompt += "Please strictly follow this format and do not include any additional text."
        prompt += "If the food is a drink (other than water), you must provide 100% accurate calories, protein, carbs, fat, and all macros. Do not treat it as water. If unsure, use the most likely drink (e.g., juice, milk, soda, etc.). Your answer must be 9999% true and never zero unless it is pure water.\n"
        prompt += "If the food is a national or regional dish (e.g., Uzbek food), you must provide 100% accurate calories, protein, carbs, fat, and all macros. If unsure, use the most likely similar dish. Your answer must be 9999% true and never zero unless it is pure water.\n"
        prompt += "If the food is a drink (e.g., Fuse Tea, Pepsi, Coca-Cola, Fanta, Sprite, juice, milk, ayran, etc.), you MUST NOT return zero for calories, protein, carbs, or fat unless it is pure water. If you do not know, estimate based on the most common value for that drink. Repeat: Never return zero for any macro for drinks except pure water. Output must be in the exact format below.\n"
        logger.info(f"Prompt sent to Gemini for user {user_id}")

        response = vision_model.generate_content([uploaded_file, prompt])
        analysis = response.text.strip()
        logger.info(f"Response from Gemini for user {user_id}: {analysis}")

        nutrition = parse_nutrition(analysis, lang)
        logger.info(f"Parsed nutrition for user {user_id}: {nutrition}")

        meal_calories = nutrition['calories']
        correct_percentage = int((nutrition['calories'] / daily_calories) * 100) if daily_calories > 0 else 0
        calories_term = terms['calories']
        # Create the regex pattern separately to avoid f-string backslash issues
        daily_req_pattern = r"\d+(\.\d+)?"
        pattern = rf'- {calories_term}: \d+(\.\d+)? kcal {daily_req_pattern}'
        replacement = f'- {calories_term}: {meal_calories} kcal {t("daily_requirement", lang, percentage=correct_percentage)} 🧮'
        analysis = re.sub(pattern, replacement, analysis)

        # Log meal if database is available
        meals_ref = get_meals_ref(user_id)
        if meals_ref is not None:
            try:
                meal_ref = meals_ref.add({
                    'timestamp': datetime.now(pytz.utc),
                    'analysis': analysis,
                    'photo_id': photo.file_id,
                    'meal_type': meal_type,
                    'calories': nutrition['calories'],
                    'protein': nutrition['protein'],
                    'carbs': nutrition['carbs'],
                    'fat': nutrition['fat'],
                    'sodium': nutrition.get('sodium', 0),
                    'fiber': nutrition.get('fiber', 0),
                    'sugar': nutrition.get('sugar', 0)
                })
                logger.info(f"Meal logged for user {user_id} with ref {meal_ref[1].id}")
                asyncio.create_task(update_streaks_and_challenges(user_id, "meal"))
            except Exception as e:
                logger.warning(f"Failed to log meal for user {user_id}: {e}")
        else:
            logger.warning(f"Database not available - meal not logged for user {user_id}")

        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(analysis)
        await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))

    except Exception as e:
        logger.error(f"Photo processing error for user {user_id}: {e}\n{traceback.format_exc()}")
        if processing_msg:
            await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))

    finally:
        if state:
            await state.clear()

@dp.message(MealLogging.waiting_for_text, F.text)
async def process_meal_text(message: types.Message, state: FSMContext):
    processing_msg = None
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        text = message.text.strip()
        if not text:
            raise ValueError("Empty text input")

        logger.info(f"Processing meal text for user {user_id}: {text}")
        data = await state.get_data()
        meal_type = data.get('meal_type', 'meal')

        get_user_ref(user_id).update({'last_active': datetime.now(pytz.utc)})
        processing_msg = await message.answer(t("processing", lang))

        language_names = {'en': 'English', 'ru': 'Russian', 'uz': 'Uzbek'}
        language = language_names.get(lang, 'English')
        terms = TRANSLATIONS["nutrition_terms"][lang]
        disclaimer = t("disclaimer", lang)
        benefit = t("benefit", lang)
        health_note = t("health_note", lang)
        recommendation = t("recommendation", lang)

        food_name = text
        user_data = get_user_ref(user_id).get().to_dict()
        daily_calories = user_data.get('daily_calories', 2000)
        prompt = f"In {language}, provide the nutritional information for {food_name} in the following format:\n\n"
        prompt += f"{t('food_analysis_header', lang, food_name=food_name)}:\n\n"
        prompt += f"- {terms['calories']}: [value] kcal {t('daily_requirement', lang, percentage='[percentage]')} 🧮\n"
        prompt += f"- {terms['protein']}: [value]g 💪\n"
        prompt += f"- {terms['carbs']}: [value]g 🍚\n"
        prompt += f"- {terms['fat']}: [value]g 🧈\n"
        prompt += f"- {terms['sodium']}: [value]mg 🧂\n"
        prompt += f"- {terms['fiber']}: [value]g 🌾\n"
        prompt += f"- {terms['sugar']}: [value]g 🍬\n\n"
        prompt += f"🌟 {benefit}: [short positive effect]\n"
        prompt += f"🩺 {health_note}: [health note]\n"
        prompt += f"💡 {recommendation}: [recommendation]\n"
        prompt += f"⚠️ {t('note_label', lang)}: {disclaimer}\n\n"
        prompt += f"Use {daily_calories} kcal as the daily calorie need for percentage calculation. If the food is not recognized, suggest a similar common food item.\n"
        prompt += "Please strictly follow this format and do not include any additional text."
        prompt += "If the food is a drink (other than water), you must provide 100% accurate calories, protein, carbs, fat, and all macros. Do not treat it as water. If unsure, use the most likely drink (e.g., juice, milk, soda, etc.). Your answer must be 9999% true and never zero unless it is pure water.\n"
        prompt += "If the food is a national or regional dish (e.g., Uzbek food), you must provide 100% accurate calories, protein, carbs, fat, and all macros. If unsure, use the most likely similar dish. Your answer must be 9999% true and never zero unless it is pure water.\n"
        prompt += "If the food is a drink (e.g., Fuse Tea, Pepsi, Coca-Cola, Fanta, Sprite, juice, milk, ayran, etc.), you MUST NOT return zero for calories, protein, carbs, or fat unless it is pure water. If you do not know, estimate based on the most common value for that drink. Repeat: Never return zero for any macro for drinks except pure water. Output must be in the exact format below.\n"
        logger.info(f"Prompt sent to Gemini for user {user_id}")

        response = nutrition_model.generate_content(prompt)
        analysis = response.text.strip()
        logger.info(f"Response from Gemini for user {user_id}: {analysis}")

        nutrition = parse_nutrition(analysis, lang)
        logger.info(f"Parsed nutrition for user {user_id}: {nutrition}")

        meal_calories = nutrition['calories']
        correct_percentage = int((nutrition['calories'] / daily_calories) * 100) if daily_calories > 0 else 0
        calories_term = terms['calories']
        # Create the regex pattern separately to avoid f-string backslash issues
        daily_req_pattern = r"\d+(\.\d+)?"
        analysis = re.sub(
            rf'- {calories_term}: \d+(\.\d+)? kcal {daily_req_pattern}',
            f'- {calories_term}: {meal_calories} kcal {t("daily_requirement", lang, percentage=correct_percentage)} 🧮',
            analysis
        )

        # Log meal if database is available
        meals_ref = get_meals_ref(user_id)
        if meals_ref is not None:
            try:
                meal_ref = meals_ref.add({
                    'timestamp': datetime.now(pytz.utc),
                    'analysis': analysis,
                    'text_input': text,
                    'meal_type': meal_type,
                    'calories': nutrition['calories'],
                    'protein': nutrition['protein'],
                    'carbs': nutrition['carbs'],
                    'fat': nutrition['fat'],
                    'sodium': nutrition.get('sodium', 0),
                    'fiber': nutrition.get('fiber', 0),
                    'sugar': nutrition.get('sugar', 0)
                })
                logger.info(f"Meal logged for user {user_id} with ref {meal_ref[1].id}")
                asyncio.create_task(update_streaks_and_challenges(user_id, "meal"))
            except Exception as e:
                logger.warning(f"Failed to log meal for user {user_id}: {e}")
        else:
            logger.warning(f"Database not available - meal not logged for user {user_id}")

        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(analysis)
        await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))

    except Exception as e:
        logger.error(f"Text processing error for user {user_id}: {e}\n{traceback.format_exc()}")
        if processing_msg:
            await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))

    finally:
        await state.clear()

@dp.message(lambda m: m.text and m.text.lower().startswith("send message"))
async def broadcast_message(message: types.Message):
    if message.from_user.id != 5080813917:
        await message.answer("⛔️ You are not authorized to use this command.\nYour ID: " + str(message.from_user.id))
        return
    broadcast_text = message.text[len("send message"):].strip()
    if not broadcast_text:
        await message.answer("Message content is empty")
        return
    progress_msg = await message.answer("Starting broadcast...")
    if db is None:
        await message.answer("❌ Database not available - cannot send broadcast message")
        return
    all_users = list(db.collection('users').stream())
    success_count = 0
    fail_count = 0
    for user_doc in all_users:
        try:
            await bot.send_message(
                chat_id=int(user_doc.id),
                text=broadcast_text
            )
            success_count += 1
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

@dp.message(Command("debug_reminders"))
async def debug_reminders(message: types.Message):
    user_id = message.from_user.id
    jobs = scheduler.get_jobs()
    user_jobs = [job for job in jobs if str(user_id) in job.id]
    log_lines = [f"Job: {job.id}, Next run: {job.next_run_time}" for job in user_jobs]
    logger.info(f"[DEBUG] Scheduled jobs for user {user_id}:\n" + "\n".join(log_lines))
    if user_jobs:
        await message.answer("\n".join(log_lines))
    else:
        await message.answer("No jobs scheduled for you.")

@dp.message(Command("logwater"))
async def logwater_alias(message: types.Message, state: FSMContext):
    await log_water(message, state)

# Admin functions
ADMIN_ID = 5080813927
BOT_USERNAME = "BiteWiseBot"  # Replace with your bot's username (without @)

def get_admin_keyboard(lang='en'):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="User List (CSV)", callback_data="admin_export_users")],
            [InlineKeyboardButton(text="User Stats", callback_data="admin_user_stats")],
            [InlineKeyboardButton(text="Force Reschedule Reminders", callback_data="admin_force_reminders")]
        ]
    )

@dp.message(lambda m: m.text and (m.text.strip().lower() == "/admin" or m.text.strip().lower() == f"/admin@{BOT_USERNAME.lower()}"))
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
        if db is None:
            await callback.answer("❌ Database not available - cannot export users", show_alert=True)
            return
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
        if db is None:
            await callback.message.answer("❌ Database not available - cannot get user stats")
            return
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
        if db is None:
            await callback.message.answer("❌ Database not available - cannot reschedule reminders")
            return
        users = list(db.collection('users').stream())
        for u in users:
            d = u.to_dict()
            user_id = int(u.id)
            timezone = d.get('timezone', 'UTC')
            await schedule_default_reminders(user_id, timezone)
        await callback.message.answer("Reminders rescheduled for all users.")
    except Exception as e:
        await callback.message.answer(f"Error rescheduling reminders: {e}")

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
                    await schedule_default_reminders(user_id, timezone)
                    logger.info(f"Scheduled reminders for user {user_id} on startup.")
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