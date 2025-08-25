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
    InlineKeyboardMarkup, InlineKeyboardButton
)
from google.cloud import firestore
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import io

# Project Directory Setup
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_DIR = os.path.join(PROJECT_DIR, "credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Translations
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
        "en": "✅ Registration complete! Welcome, {name}! Send me food info or photos.",
        "ru": "✅ Регистрация завершена! Добро пожаловать, {name}! Отправьте информацию о еде.",
        "uz": "✅ Ro'yxatdan o'tish yakunlandi! Xush kelibsiz, {name}! Ovqat haqida ma'lumot yuboring."
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
              "• /logfood - Log a meal\n\n"
              "<b>How to Use:</b>\n"
              "1. <b>Log Meals:</b> Use /logfood or the 🍽 button to select meal type and describe your meal or send a photo.\n"
              "2. <b>Log Water:</b> Use /water or the 💧 button to log water intake.\n"
              "3. <b>View Stats:</b> Use /stats or the 📊 button to see your nutrition statistics.\n"
              "4. <b>Settings:</b> Use /settings or the ⚙️ button to change language, edit profile, or manage reminders.\n"
              "5. <b>Help:</b> Use /help or the ❓ button anytime for assistance.\n\n"
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
              "• /logfood - Записать прием пищи\n\n"
              "<b>Как использовать:</b>\n"
              "1. <b>Запись питания:</b> Используйте /logfood или кнопку 🍽, чтобы выбрать тип приема пищи и описать его или отправить фото.\n"
              "2. <b>Запись воды:</b> Используйте /water или кнопку 💧 для записи приема воды.\n"
              "3. <b>Просмотр статистики:</b> Используйте /stats или кнопку 📊 для просмотра статистики питания.\n"
              "4. <b>Настройки:</b> Используйте /settings или кнопку ⚙️ для изменения языка, редактирования профиля или управления напоминаниями.\n"
              "5. <b>Помощь:</b> Используйте /help или кнопку ❓ в любое время для получения помощи.\n\n"
              "Для дополнительной помощи обратитесь к @jurat1\n"
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
              "• /logfood - Ovqat qayd etish\n\n"
              "<b>Qanday foydalanish:</b>\n"
              "1. <b>Ovqat qayd etish:</b> /logfood yoki 🍽 tugmasini ishlatib, ovqat turini tanlang va tasvirlang yoki rasm yuboring.\n"
              "2. <b>Suv qayd etish:</b> /water yoki 💧 tugmasini ishlatib suv iste'molini qayd eting.\n"
              "3. <b>Statistikani ko'rish:</b> /stats yoki 📊 tugmasini ishlatib ovqatlanish statistikasini ko'ring.\n"
              "4. <b>Sozlamalar:</b> /settings yoki ⚙️ tugmasini ishlatib tilni o'zgartiring, profilingizni tahrirlang yoki eslatmalarni boshqaring.\n"
              "5. <b>Yordam:</b> Istalgan vaqtda /help yoki ❓ tugmasini ishlatib yordam oling.\n\n"
              "Qo'shimcha yordam uchun @jurat1 ga murojaat qiling\n"
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
        "ru": "Сводка за сегодня",
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
        "en": {"calories": "Calories", "protein": "Protein", "carbs": "Carbs", "fat": "Fat"},
        "ru": {"calories": "Калории", "protein": "Белок", "carbs": "Углеводы", "fat": "Жиры"},
        "uz": {"calories": "Kaloriyasi", "protein": "Oqsil", "carbs": "Uglevodlar", "fat": "Yog'lar"}
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
    "weekly_summary": {
        "en": "📅 Your Weekly Summary\n\n{insights}",
        "ru": "📅 Ваша недельная сводка\n\n{insights}",
        "uz": "📅 Haftalik xulosa\n\n{insights}"
    },
    "confirm_log": {
        "en": "👍 Logged Correctly",
        "ru": "👍 Записано правильно",
        "uz": "👍 To'g'ri qayd etildi"
    },
    "add_note": {
        "en": "➕ Add a Note",
        "ru": "➕ Добавить заметку",
        "uz": "➕ Eslatma qo'shish"
    },
    "log_similar": {
        "en": "🔄 Log Similar Meal",
        "ru": "🔄 Записать похожее блюдо",
        "uz": "🔄 Shu kabi ovqatni qayd etish"
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
        "en": "You have reached the recommended daily water intake. Drinking more may lead to overhydration, which can be harmful.",
        "ru": "Вы достигли рекомендуемой суточной нормы потребления воды. Употребление большего количества может привести к переувлажнению, что может быть вредно.",
        "uz": "Siz kunlik suv iste'molining tavsiya etilgan miqdoriga yetdingiz. Ko'proq ichish ortiqcha suvlanishga olib kelishi mumkin, bu zararli bo'lishi mumkin."
    }
}

def t(key: str, lang: str, **kwargs) -> str:
    base = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
    return base.format(**kwargs) if kwargs else base

# Initialize Services
load_dotenv()

try:
    db = firestore.Client()
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client(project="nutrition-bot-local")

def get_user_ref(user_id: int):
    return db.collection('users').document(str(user_id))

def get_meals_ref(user_id: int):
    return get_user_ref(user_id).collection('meals')

def get_water_ref(user_id: int):
    return get_user_ref(user_id).collection('water')

def get_streaks_ref(user_id: int):
    return get_user_ref(user_id).collection('streaks')

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    nutrition_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")

# Bot Setup
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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

class ReminderStates(StatesGroup):
    setting_water = State()
    setting_meal = State()

class MealLogging(StatesGroup):
    selecting_type = State()
    waiting_for_text = State()
    waiting_for_note = State()

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

def get_goals_keyboard(lang: str):
    uz_buttons = [
        ("⚖ Vazn kamaytirish", "lose_weight"),
        ("💪 Massa oshirish", "gain_muscle"),
        ("🥗 Sog'lom ovqat", "eat_healthier"),
        ("👶 Yoshroq ko'rinish", "look_younger"),
        ("❓ Boshqa maqsad", "other_goal")
    ]
    buttons = []
    if lang == "uz":
        for text, goal_key in uz_buttons:
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_goal_{goal_key}")])
    else:
        goals = ["lose_weight", "gain_muscle", "eat_healthier", "look_younger", "other_goal"]
        for goal in goals:
            text = t(goal, lang)
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_goal_{goal}")])
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
    buttons = [InlineKeyboardButton(text=t(meal_type, lang), callback_data=f"meal_type_{meal_type}") for meal_type in meal_types]
    cancel_button = InlineKeyboardButton(text=t("cancel_action", lang), callback_data="cancel_meal_logging")
    return InlineKeyboardMarkup(inline_keyboard=[buttons, [cancel_button]])

def get_meal_action_keyboard(lang: str, meal_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("log_similar", lang), callback_data=f"similar_{meal_id}")]
    ])

# Helper Functions
async def get_user_language(user_id: int) -> str:
    try:
        doc = get_user_ref(user_id).get()
        return doc.to_dict().get('language', 'en') if doc.exists else 'en'
    except Exception as e:
        logger.error(f"Language fetch failed for user {user_id}: {e}")
        return 'en'

def parse_nutrition(analysis: str) -> dict:
    nutrition = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0
    }
    lines = analysis.split('\n')
    for line in lines:
        if line.strip().startswith('-'):
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip().lower()
                value_str = parts[0].strip()
                value = re.search(r'\d+(\.\d+)?', value_str)
                if value:
                    nutrition_key = {
                        "calories": "calories",
                        "protein": "protein",
                        "carbs": "carbs",
                        "fat": "fat",
                        "калории": "calories",
                        "белок": "protein",
                        "углеводы": "carbs",
                        "жиры": "fat",
                        "kaloriyasi": "calories",
                        "oqsil": "protein",
                        "uglevodlar": "carbs",
                        "yog'lar": "fat"
                    }.get(key, None)
                    if nutrition_key:
                        nutrition[nutrition_key] = float(value.group())
    return nutrition

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
            await bot.send_message(user_id, t("streak_message", lang, type=log_type, days=streak_data['count']))
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
        await bot.send_message(user_id, t("badge_earned", lang, badge="Water Warrior"))

    if log_type == "meal":
        total_meals = len(list(get_meals_ref(user_id).stream()))
        if total_meals >= 50 and not badges.get("50_meals"):
            badges["50_meals"] = True
            badges_ref.set(badges)
            await bot.send_message(user_id, t("badge_earned", lang, badge="Meal Master"))

# Internal function to handle water logging with checks
async def _log_water_internal(user_id: int, lang: str) -> str:
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        if not user_data:
            return "error"
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(tz).date()
        today_start = tz.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
        today_end = tz.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)
        weight = user_data.get('weight', 70)
        daily_limit_ml = int(weight * 40 * 1.5)
        water_ref = get_water_ref(user_id)
        today_water_docs = list(water_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).order_by('timestamp', direction=firestore.Query.DESCENDING).stream())
        if today_water_docs:
            most_recent = today_water_docs[0].to_dict()
            if (datetime.now(pytz.utc) - most_recent['timestamp']).total_seconds() < 300:  # 5 minutes
                return "cooldown"
            total_water_today = sum(doc.to_dict()['amount'] for doc in today_water_docs)
            if total_water_today + 250 > daily_limit_ml:
                return "overhydration"
        # Log water intake
        get_water_ref(user_id).add({
            'amount': 250,
            'timestamp': datetime.now(pytz.utc)
        })
        await update_streaks_and_challenges(user_id, "water")
        return "success"
    except Exception as e:
        logger.error(f"Error in _log_water_internal for user {user_id}: {e}")
        return "error"

# Reminder Functions
async def schedule_default_reminders(user_id: int, timezone: str):
    try:
        for job in scheduler.get_jobs():
            parts = job.id.split('_')
            if len(parts) >= 2 and parts[1] == str(user_id):
                job.remove()

        user_data = get_user_ref(user_id).get().to_dict()
        tz = pytz.timezone(timezone)

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
                    replace_existing=True
                )

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
                    replace_existing=True
                )

        if user_data.get('motivational_quotes_enabled', True):
            scheduler.add_job(
                send_motivational_quote,
                'cron',
                hour=21,
                minute=0,
                timezone=timezone,
                args=[user_id],
                id=f"motivation_{user_id}",
                replace_existing=True
            )

        if user_data.get('breakfast_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=8,
                minute=0,
                timezone=timezone,
                args=[user_id, 'breakfast'],
                id=f"breakfast_{user_id}",
                replace_existing=True
            )

        if user_data.get('lunch_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=12,
                minute=0,
                timezone=timezone,
                args=[user_id, 'lunch'],
                id=f"lunch_{user_id}",
                replace_existing=True
            )

        if user_data.get('dinner_reminder_enabled', True):
            scheduler.add_job(
                send_meal_reminder,
                'cron',
                hour=18,
                minute=0,
                timezone=timezone,
                args=[user_id, 'dinner'],
                id=f"dinner_{user_id}",
                replace_existing=True
            )

        scheduler.add_job(
            send_weekly_summary,
            'cron',
            day_of_week='sun',
            hour=20,
            timezone=timezone,
            args=[user_id],
            id=f"summary_{user_id}",
            replace_existing=True
        )

        logger.info(f"Scheduled reminders for user {user_id}")
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
            inline_keyboard=[[InlineKeyboardButton(text="✅ Log Water", callback_data="log_water")]]
        )
        await bot.send_message(user_id, message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending water reminder to user {user_id}: {e}")

async def send_meal_reminder(user_id: int, meal_type: str):
    try:
        user_lang = await get_user_language(user_id)
        emoji_map = {"breakfast": "🍳", "lunch": "🍲", "dinner": "🍽"}
        emoji = emoji_map.get(meal_type, "🍔")
        message = f"{emoji} {t('meal_reminder', user_lang, meal_type=t(meal_type, user_lang))}"
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
        logger.error(f"Error sending meal reminder to user {user_id}: {e}")

async def send_motivational_quote(user_id: int):
    try:
        user_ref = get_user_ref(user_id)
        user_data = user_ref.get().to_dict()
        if not user_data.get('motivational_quotes_enabled', True):
            return

        lang = user_data.get('language', 'en')
        goal = user_data.get('goal', '')
        user_name = user_data.get('name', 'User')

        if not goal:
            default_goal = t("eat_healthier", lang)
            user_ref.update({'goal': default_goal})
            goal = default_goal

        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(tz).date()
        today_start = tz.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
        today_end = tz.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)

        meals_ref = get_meals_ref(user_id)
        today_meal_docs = list(meals_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_calories = sum(m.to_dict().get('calories', 0) for m in today_meal_docs)

        water_ref = get_water_ref(user_id)
        today_water_docs = list(water_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        today_water = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)

        advice = ""
        if "lose_weight" in goal.lower():
            advice = t("lose_weight", lang) + ": "
            if today_calories > 2000:
                advice += "You've eaten quite a bit today. Try lighter meals tomorrow. "
            else:
                advice += "Great job keeping calories in check! "
        elif "gain_muscle" in goal.lower():
            advice = t("gain_muscle", lang) + ": "
            if today_calories < 2500:
                advice += "You might need to eat more to build muscle. "
            else:
                advice += "Good intake for muscle growth! "
        elif "eat_healthier" in goal.lower():
            advice = t("eat_healthier", lang) + ": Focus on whole foods. "
        elif "look_younger" in goal.lower():
            advice = t("look_younger", lang) + ": Eat antioxidant-rich foods. "

        advice += "Drink water, sleep early, and wake up on time for a healthy day!"

        prompt = (f"Generate a 2-3 sentence motivational message in {lang} "
                  f"addressed to {user_name}, who has the goal: {goal}. "
                  f"Include stats: calories today ({today_calories} kcal), water ({today_water} ml). "
                  f"Provide advice: {advice} "
                  f"Start with their name and use 2-3 emojis.")

        try:
            response = nutrition_model.generate_content(prompt)
            quote = response.text.strip()
            quote = f"✅ {quote}"
        except Exception as e:
            logger.error(f"Failed to generate quote for user {user_id}: {e}")
            quote = (f"✅ {user_name}, {t('default_motivational_quote', lang)}\n"
                     f"Stats: {today_calories} kcal, {today_water} ml water today.\n"
                     f"Advice: {advice}")

        await bot.send_message(
            user_id,
            f"══════════════\n"
            f"{quote}\n"
            f"══════════════\n\n"
            f"⏰ Daily stats and tips at 9 PM ({user_data.get('timezone', 'UTC')})",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error in motivational quote for user {user_id}: {e}")

async def send_weekly_summary(user_id: int):
    try:
        user_data = get_user_ref(user_id).get().to_dict()
        lang = user_data.get('language', 'en')
        tz = pytz.timezone(user_data.get('timezone', 'UTC'))

        week_start = datetime.now(tz).date() - timedelta(days=7)
        week_end = datetime.now(tz).date()
        week_start_utc = tz.localize(datetime.combine(week_start, datetime.min.time())).astimezone(pytz.UTC)
        week_end_utc = tz.localize(datetime.combine(week_end, datetime.max.time())).astimezone(pytz.UTC)

        meals = list(get_meals_ref(user_id).where('timestamp', '>=', week_start_utc).where('timestamp', '<=', week_end_utc).stream())
        total_calories = sum(m.to_dict().get('calories', 0) for m in meals)
        total_protein = sum(m.to_dict().get('protein', 0) for m in meals)
        total_carbs = sum(m.to_dict().get('carbs', 0) for m in meals)
        total_fat = sum(m.to_dict().get('fat', 0) for m in meals)

        insights = f"Total Calories: {total_calories} kcal\n"
        insights += f"Total Protein: {total_protein}g\n"
        insights += f"Total Carbs: {total_carbs}g\n"
        insights += f"Total Fat: {total_fat}g\n"

        await bot.send_message(user_id, t("weekly_summary", lang, insights=insights))
    except Exception as e:
        logger.error(f"Error sending weekly summary to user {user_id}: {e}")

# Handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    if user_ref.get().exists:
        lang = await get_user_language(user_id)
        await message.answer(t("already_registered", lang) + "\n\n" + t("reminders_enabled_note", lang), reply_markup=get_main_menu_keyboard(lang))
    else:
        await state.clear()
        await message.answer(t("intro", "en"), reply_markup=get_language_inline_keyboard())
        await state.set_state(Registration.language)

@dp.callback_query(F.data.startswith("set_lang_"), StateFilter(Registration.language))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang_code = callback.data.split("_")[-1]
        if lang_code not in ["en", "ru", "uz"]:
            await callback.answer(t("error_processing", "en"))
            return
        await state.update_data(language=lang_code)
        await callback.message.edit_text(
            f"{t('language_selected', lang_code)}\n\n{t('ask_name', lang_code)}",
            reply_markup=None
        )
        await callback.answer()
        await state.set_state(Registration.name)
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

@dp.callback_query(F.data.startswith("set_goal_"), StateFilter(Registration.goal))
async def process_goal_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        goal_key = callback.data.split("_")[-1]
        lang = (await state.get_data()).get("language", "en")

        goal_translations = {
            "uz": {
                "lose_weight": "⚖ Vazn kamaytirish",
                "gain_muscle": "💪 Massa oshirish",
                "eat_healthier": "🥗 Sog'lom ovqat",
                "look_younger": "👶 Yoshroq ko'rinish",
                "other_goal": "❓ Boshqa maqsad"
            }
        }
        goal_text = goal_translations.get(lang, {}).get(goal_key, t(goal_key, lang))

        await state.update_data(goal=goal_text)
        data = await state.get_data()

        user_ref = get_user_ref(user_id)
        user_data = {
            **data,
            'registered_at': datetime.now(pytz.utc),
            'telegram_username': callback.from_user.username,
            'telegram_id': user_id,
            'last_active': datetime.now(pytz.utc),
            'water_reminders': True,
            'meal_reminders': True,
            'motivational_quotes_enabled': True,
            'breakfast_reminder_enabled': True,
            'lunch_reminder_enabled': True,
            'dinner_reminder_enabled': True
        }

        user_ref.set(user_data)
        await schedule_default_reminders(user_id, data['timezone'])

        await callback.message.delete()
        await bot.send_message(
            user_id,
            t("registration_complete", lang, name=data['name']) + "\n\n" + t("reminders_enabled_note", lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Goal selection error: {str(e)}")
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(t("error_processing", lang))
        await state.clear()
    await callback.answer()

@dp.message(Registration.goal)
async def reg_goal(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        lang = data.get("language", "en")
        goal = message.text.strip()

        skip_values = ["Skip", "Пропустить", "O'tkaz"]
        goal_value = "" if goal in skip_values else goal

        user_ref = get_user_ref(message.from_user.id)
        user_data = {
            **data,
            'goal': goal_value,
            'registered_at': datetime.now(pytz.utc),
            'telegram_username': message.from_user.username,
            'telegram_id': message.from_user.id,
            'last_active': datetime.now(pytz.utc),
            'water_reminders': True,
            'meal_reminders': True,
            'motivational_quotes_enabled': True,
            'breakfast_reminder_enabled': True,
            'lunch_reminder_enabled': True,
            'dinner_reminder_enabled': True
        }

        user_ref.set(user_data)
        await schedule_default_reminders(message.from_user.id, data['timezone'])

        await message.answer(t("registration_complete", lang, name=data['name']) + "\n\n" + t("reminders_enabled_note", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.clear()
    except Exception as e:
        logger.error(f"Registration error for user {message.from_user.id}: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("error_processing", lang))
        await state.clear()

@dp.message(F.text.lower() == "💧 log water")
@dp.message(F.text.lower() == "💧 записать воду")
@dp.message(F.text.lower() == "💧 suv qayd etish")
@dp.message(Command("water"))
async def log_water(message: types.Message):
    try:
        user_id = message.from_user.id
        lang = await get_user_language(user_id)
        get_user_ref(user_id).update({'last_active': datetime.now(pytz.utc)})
        result = await _log_water_internal(user_id, lang)
        if result == "cooldown":
            await message.answer(t("cooldown_message", lang))
        elif result == "overhydration":
            await message.answer(t("overhydration_warning", lang))
        elif result == "success":
            await message.answer(t("water_logged", lang), reply_markup=get_main_menu_keyboard(lang))
        else:
            await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Water logging error for user {user_id}: {e}")
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))

@dp.callback_query(lambda c: c.data == "log_water")
async def callback_log_water(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        lang = await get_user_language(user_id)
        get_user_ref(user_id).update({'last_active': datetime.now(pytz.utc)})
        result = await _log_water_internal(user_id, lang)
        if result == "cooldown":
            await bot.send_message(user_id, t("cooldown_message", lang))
        elif result == "overhydration":
            await bot.send_message(user_id, t("overhydration_warning", lang))
        elif result == "success":
            await bot.send_message(user_id, t("water_logged", lang), reply_markup=get_main_menu_keyboard(lang))
        else:
            await bot.send_message(user_id, t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Water logging error from callback for user {user_id}: {e}")
        await bot.send_message(user_id, t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))

@dp.message(F.text.lower() == "📊 my stats")
@dp.message(F.text.lower() == "📊 моя статистика")
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
            return await message.answer(t("error_processing", lang) + " User data not found.", reply_markup=get_main_menu_keyboard(lang))

        tz = pytz.timezone(user_data.get('timezone', 'UTC'))
        today = datetime.now(tz).date()
        today_start = tz.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
        today_end = tz.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)

        water_ref = get_water_ref(user_id)
        today_water_docs = list(water_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        logger.info(f"Fetched {len(today_water_docs)} water logs for user {user_id} today")
        today_water = sum(doc.to_dict().get('amount', 0) for doc in today_water_docs)
        total_water = sum(doc.to_dict().get('amount', 0) for doc in water_ref.stream())

        meals_ref = get_meals_ref(user_id)
        today_meal_docs = list(meals_ref.where('timestamp', '>=', today_start).where('timestamp', '<=', today_end).stream())
        logger.info(f"Fetched {len(today_meal_docs)} meal logs for user {user_id} today")
        today_meals = len(today_meal_docs)
        today_calories = sum(m.to_dict().get('calories', 0) for m in today_meal_docs)
        today_protein = sum(m.to_dict().get('protein', 0) for m in today_meal_docs)
        today_carbs = sum(m.to_dict().get('carbs', 0) for m in today_meal_docs)
        today_fat = sum(m.to_dict().get('fat', 0) for m in today_meal_docs)

        all_meal_docs = list(meals_ref.stream())
        total_meals = len(all_meal_docs)
        total_calories = sum(m.to_dict().get('calories', 0) for m in all_meal_docs)

        weight = user_data.get('weight', 70)
        recommended_water = int(weight * 40)
        water_percentage = min(int((today_water / recommended_water) * 100), 100) if recommended_water > 0 else 0
        progress_bar_length = 10
        filled_blocks = int((water_percentage / 100) * progress_bar_length)
        progress_bar = "🟦" * filled_blocks + "⬜" * (progress_bar_length - filled_blocks)

        response = (
            f"📊 <b>{t('stats_header', lang)}:</b>\n\n"
            f"<b>{t('today_summary', lang)} ({today.strftime('%Y-%m-%d')}):</b>\n"
            f"💧 <b>{t('water', lang)}:</b> {today_water}ml / {recommended_water}ml\n"
            f"{progress_bar} {water_percentage}%\n"
            f"🍽 <b>{t('meals_today', lang)}:</b> {today_meals}\n"
            f"⚡ <b>Total Calories Today:</b> {today_calories} kcal\n"
            f"💪 <b>Total Protein Today:</b> {today_protein}g\n"
            f"🍚 <b>Total Carbs Today:</b> {today_carbs}g\n"
            f"🥑 <b>Total Fat Today:</b> {today_fat}g\n\n"
            f"<b>{t('total_stats', lang)}:</b>\n"
            f"💧 <b>{t('total_water', lang)}:</b> {total_water}ml\n"
            f"🍽 <b>{t('total_meals', lang)}:</b> {total_meals}\n"
            f"🔥 <b>Total Calories All Time:</b> {total_calories} kcal\n"
        )

        if 'height' in user_data and 'weight' in user_data:
            height_m = user_data['height'] / 100
            bmi = user_data['weight'] / (height_m * height_m)
            bmi_categories = {
                "en": {"underweight": "Underweight", "normal": "Normal weight", "overweight": "Overweight", "obesity": "Obesity"},
                "ru": {"underweight": "Недостаточный вес", "normal": "Нормальный вес", "overweight": "Избыточный вес", "obesity": "Ожирение"},
                "uz": {"underweight": "Kam vazn", "normal": "Normal vazn", "overweight": "Ortiqcha vazn", "obesity": "Semizlik"}
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

    await callback.message.edit_text(t("edit_which_field", lang), reply_markup=keyboard)
    await state.set_state(EditProfileStates.selecting_field)

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
        await message.answer(t("profile_updated", lang), reply_markup=get_main_menu_keyboard(lang))
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
            get_user_ref(user_id).update({'age': new_age})
            await message.answer(t("profile_updated", lang), reply_markup=get_main_menu_keyboard(lang))
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
            get_user_ref(user_id).update({'height': new_height})
            await message.answer(t("profile_updated", lang), reply_markup=get_main_menu_keyboard(lang))
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
            get_user_ref(user_id).update({'weight': new_weight})
            await message.answer(t("profile_updated", lang), reply_markup=get_main_menu_keyboard(lang))
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
    motivation_status = t("reminder_enabled" if user_data.get('motivational_quotes_enabled', True) else "reminder_disabled", lang)
    breakfast_status = t("reminder_enabled" if user_data.get('breakfast_reminder_enabled', True) else "reminder_disabled", lang)
    lunch_status = t("reminder_enabled" if user_data.get('lunch_reminder_enabled', True) else "reminder_disabled", lang)
    dinner_status = t("reminder_enabled" if user_data.get('dinner_reminder_enabled', True) else "reminder_disabled", lang)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t('toggle_water_reminders', lang)} ({water_status})", callback_data="toggle_water")],
        [InlineKeyboardButton(text=f"{t('toggle_meal_reminders', lang)} ({meal_status})", callback_data="toggle_meal")],
        [InlineKeyboardButton(text=f"{t('toggle_motivational_quotes', lang)} ({motivation_status})", callback_data="toggle_motivation")],
        [InlineKeyboardButton(text=f"{t('toggle_breakfast_reminder', lang)} ({breakfast_status})", callback_data="toggle_breakfast")],
        [InlineKeyboardButton(text=f"{t('toggle_lunch_reminder', lang)} ({lunch_status})", callback_data="toggle_lunch")],
        [InlineKeyboardButton(text=f"{t('toggle_dinner_reminder', lang)} ({dinner_status})", callback_data="toggle_dinner")],
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

    if action in ["toggle_water", "toggle_meal", "toggle_motivation", "toggle_breakfast", "toggle_lunch", "toggle_dinner"]:
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
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="edit_profile")]
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
            [InlineKeyboardButton(text=t("edit_profile", lang), callback_data="edit_profile")]
        ]
    )

    await callback.message.edit_text(t("settings_title", lang), reply_markup=settings_kb)
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

        logger.info(f"Uploading photo to Gemini for user {user_id}")
        uploaded_file = genai.upload_file(file_io, mime_type="image/jpeg")
        prompt = f"In {language}, analyze this food image and provide nutritional information in the following format:\n\n"
        prompt += f"Oziqaviy qiymat:\n\n"
        prompt += f"- {terms['calories']}: [value] 🧮\n"
        prompt += f"- {terms['protein']}: [value]g 💪\n"
        prompt += f"- {terms['carbs']}: [value]g 🍚\n"
        prompt += f"- {terms['fat']}: [value]g 🧈\n\n"
        prompt += f"🌟 {benefit}: [short positive effect]\n"
        prompt += f"⚠️ {t('note_label', lang)}: {disclaimer}\n\n"
        prompt += "If the food is not recognized, suggest a similar common food item.\n"
        prompt += "Please strictly follow this format and do not include any additional text."
        logger.info(f"Prompt sent to Gemini for user {user_id}")

        response = vision_model.generate_content([uploaded_file, prompt])
        analysis = response.text.strip()
        logger.info(f"Response from Gemini for user {user_id}: {analysis}")

        nutrition = parse_nutrition(analysis)
        logger.info(f"Parsed nutrition for user {user_id}: {nutrition}")

        meal_ref = get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'photo_id': photo.file_id,
            'meal_type': meal_type,
            'calories': nutrition['calories'],
            'protein': nutrition['protein'],
            'carbs': nutrition['carbs'],
            'fat': nutrition['fat']
        })
        logger.info(f"Meal logged for user {user_id} with ref {meal_ref[1].id}")
        await update_streaks_and_challenges(user_id, "meal")

        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(analysis, reply_markup=get_meal_action_keyboard(lang, meal_ref[1].id))
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

        food_name = text
        prompt = f"In {language}, provide the nutritional information for {food_name} in the following format:\n\n"
        prompt += f"{food_name} uchun oziqaviy qiymat:\n\n"
        prompt += f"- {terms['calories']}: [value] 🧮\n"
        prompt += f"- {terms['protein']}: [value]g 💪\n"
        prompt += f"- {terms['carbs']}: [value]g 🍚\n"
        prompt += f"- {terms['fat']}: [value]g 🧈\n\n"
        prompt += f"🌟 {benefit}: [short positive effect]\n"
        prompt += f"⚠️ {t('note_label', lang)}: {disclaimer}\n\n"
        prompt += "If the food is not recognized, suggest a similar common food item.\n"
        prompt += "Please strictly follow this format and do not include any additional text."
        logger.info(f"Prompt sent to Gemini for user {user_id}")

        response = nutrition_model.generate_content(prompt)
        analysis = response.text.strip()
        logger.info(f"Response from Gemini for user {user_id}: {analysis}")

        nutrition = parse_nutrition(analysis)
        logger.info(f"Parsed nutrition for user {user_id}: {nutrition}")

        meal_ref = get_meals_ref(user_id).add({
            'timestamp': datetime.now(pytz.utc),
            'analysis': analysis,
            'text_input': text,
            'meal_type': meal_type,
            'calories': nutrition['calories'],
            'protein': nutrition['protein'],
            'carbs': nutrition['carbs'],
            'fat': nutrition['fat']
        })
        logger.info(f"Meal logged for user {user_id} with ref {meal_ref[1].id}")
        await update_streaks_and_challenges(user_id, "meal")

        await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(analysis, reply_markup=get_meal_action_keyboard(lang, meal_ref[1].id))
        await message.answer(t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))

    except Exception as e:
        logger.error(f"Meal text processing error for user {user_id}: {e}\n{traceback.format_exc()}")
        if processing_msg:
            await bot.delete_message(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        await message.answer(t("error_processing", lang), reply_markup=get_main_menu_keyboard(lang))

    finally:
        await state.clear()

@dp.message(F.text.lower() == "🍽 log meal")
@dp.message(F.text.lower() == "🍽 записать прием пищи")
@dp.message(F.text.lower() == "🍽 ovqat qayd etish")
@dp.message(Command("logfood"))
@dp.message(Command("logmeal"))
async def log_meal_prompt(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(MealLogging.selecting_type)
    await message.answer(t("select_meal_type", lang), reply_markup=get_meal_type_keyboard(lang))

@dp.callback_query(MealLogging.selecting_type, F.data.startswith("meal_type_"))
async def process_meal_type_selection(callback: types.CallbackQuery, state: FSMContext):
    meal_type = callback.data.split("_")[-1]
    lang = await get_user_language(callback.from_user.id)
    await state.update_data(meal_type=meal_type)
    await state.set_state(MealLogging.waiting_for_text)
    await callback.message.edit_text(t("describe_meal", lang).format(meal_type=t(meal_type, lang)))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "cancel_meal_logging")
async def cancel_meal_logging(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.clear()
    await callback.message.edit_text(t("action_canceled", lang), reply_markup=None)
    await bot.send_message(user_id, t("main_menu", lang), reply_markup=get_main_menu_keyboard(lang))
    await callback.answer()

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    await state.clear()
    await message.answer(t("action_canceled", lang), reply_markup=get_main_menu_keyboard(lang))

# Main
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())