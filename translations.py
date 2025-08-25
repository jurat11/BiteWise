from typing import Dict, Any

# Copy the translations from main3.py
TRANSLATIONS: Dict[str, Dict[str, str]] = {
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
    "menu_log_meal": {
        "en": "🍽 Log Meal",
        "ru": "🍽 Записать прием пищи",
        "uz": "🍽 Ovqat qayd etish"
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
    "menu_help": {
        "en": "❓ Help",
        "ru": "❓ Помощь",
        "uz": "❓ Yordam"
    },
    "edit_profile": {
        "en": "👤 Edit Profile",
        "ru": "👤 Редактировать профиль",
        "uz": "👤 Profilni tahrirlash"
    },
    "edit_reminders": {
        "en": "⏰ Edit Reminders",
        "ru": "⏰ Редактировать напоминания",
        "uz": "⏰ Eslatmalarni tahrirlash"
    },
    "change_language": {
        "en": "🔤 Change Language",
        "ru": "🔤 Изменить язык",
        "uz": "🔤 Tilni o'zgartirish"
    },
    "edit_body_fat": {
        "en": "📊 Update Body Fat %",
        "ru": "📊 Обновить % жира",
        "uz": "📊 Tana yog'ini yangilash"
    },
    "back_to_settings": {
        "en": "🔙 Back",
        "ru": "🔙 Назад",
        "uz": "🔙 Orqaga"
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
        "uz": "Snacklar"
    },
    "enter_custom_amount": {
        "en": "Enter Custom Amount",
        "ru": "Ввести свое значение",
        "uz": "Boshqa miqdorni kiritish"
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
    "edit_which_field": {
        "en": "Select field to edit:",
        "ru": "Выберите поле для редактирования:",
        "uz": "Tahrirlash uchun maydonni tanlang:"
    },
    "profile_updated": {
        "en": "✅ Profile updated successfully!",
        "ru": "✅ Профиль успешно обновлен!",
        "uz": "✅ Profil muvaffaqiyatli yangilandi!"
    },
    "settings_title": {
        "en": "⚙️ Settings",
        "ru": "⚙️ Настройки",
        "uz": "⚙️ Sozlamalar"
    },
    "main_menu": {
        "en": "📋 Main Menu",
        "ru": "📋 Главное меню",
        "uz": "📋 Asosiy menyu"
    }
}

def t(key: str, lang: str, **kwargs) -> str:
    """Get translation for given key and language with optional format parameters."""
    base = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
    return base.format(**kwargs) if kwargs else base 