from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from ..locales.translations import t

def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get main menu keyboard"""
    keyboard = [
        [
            KeyboardButton(text=t("menu_log_meal", lang)),
            KeyboardButton(text=t("menu_log_water", lang))
        ],
        [
            KeyboardButton(text=t("menu_stats", lang)),
            KeyboardButton(text=t("menu_settings", lang))
        ],
        [KeyboardButton(text=t("menu_help", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_language_keyboard() -> ReplyKeyboardMarkup:
    """Get language selection keyboard"""
    keyboard = [
        [
            KeyboardButton(text="🇺🇸 English"),
            KeyboardButton(text="🇷🇺 Русский"),
            KeyboardButton(text="🇺🇿 O'zbek")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_water_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get water logging keyboard"""
    keyboard = [
        [
            KeyboardButton(text="100 ml"),
            KeyboardButton(text="250 ml")
        ],
        [
            KeyboardButton(text="500 ml"),
            KeyboardButton(text=t("enter_custom_amount", lang))
        ],
        [KeyboardButton(text=t("cancel_action", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_meal_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get meal type keyboard"""
    keyboard = [
        [
            KeyboardButton(text=t("breakfast", lang)),
            KeyboardButton(text=t("lunch", lang))
        ],
        [
            KeyboardButton(text=t("dinner", lang)),
            KeyboardButton(text=t("snack", lang))
        ],
        [KeyboardButton(text=t("cancel_action", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_settings_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get settings menu keyboard"""
    keyboard = [
        [KeyboardButton(text=t("change_language", lang))],
        [KeyboardButton(text=t("edit_reminders", lang))],
        [KeyboardButton(text=t("update_body_fat", lang))],
        [KeyboardButton(text=t("back_to_settings", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_reminder_settings_keyboard(lang: str, water_enabled: bool, meal_enabled: bool) -> ReplyKeyboardMarkup:
    """Get reminder settings keyboard"""
    water_status = t("reminder_enabled", lang) if water_enabled else t("reminder_disabled", lang)
    meal_status = t("reminder_enabled", lang) if meal_enabled else t("reminder_disabled", lang)
    
    keyboard = [
        [KeyboardButton(text=f"💧 {t('toggle_water_reminders', lang)} ({water_status})")],
        [KeyboardButton(text=f"🍽 {t('toggle_meal_reminders', lang)} ({meal_status})")],
        [KeyboardButton(text=t("back_to_settings", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_body_fat_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get body fat selection keyboard"""
    keyboard = []
    for range_key in ["5-10", "10-15", "15-20", "20-25", "25-30", "30-plus"]:
        keyboard.append([KeyboardButton(text=t(f"bf_range_{range_key}", lang))])
    keyboard.append([KeyboardButton(text=t("bf_idk", lang))])
    keyboard.append([KeyboardButton(text=t("cancel_action", lang))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_yes_no_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Get yes/no keyboard"""
    keyboard = [
        [
            KeyboardButton(text=t("yes", lang)),
            KeyboardButton(text=t("no", lang))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True) 