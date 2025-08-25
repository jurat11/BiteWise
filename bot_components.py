from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from translations import t

# State Classes
class UserRegistration(StatesGroup):
    selecting_language = State()
    entering_name = State()
    entering_age = State()
    entering_height = State()
    entering_weight = State()
    selecting_gender = State()
    selecting_timezone = State()
    selecting_goal = State()
    selecting_activity = State()
    entering_body_fat = State()

class MealLogging(StatesGroup):
    selecting_type = State()
    entering_description = State()
    processing_photo = State()

class WaterLogStates(StatesGroup):
    choosing_amount = State()
    entering_custom_amount = State()

class SettingsStates(StatesGroup):
    main_menu = State()
    editing_profile = State()
    editing_reminders = State()
    editing_language = State()
    editing_body_fat = State()

# Keyboard Generation Functions
def get_language_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🇺🇸 English"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇺🇿 O'zbek")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_gender_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t("male", lang)), KeyboardButton(text=t("female", lang))],
        [KeyboardButton(text=t("cancel_action", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_meal_type_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t("breakfast", lang)), KeyboardButton(text=t("lunch", lang))],
        [KeyboardButton(text=t("dinner", lang)), KeyboardButton(text=t("snack", lang))],
        [KeyboardButton(text=t("cancel_action", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_water_log_options_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="250 ml"), KeyboardButton(text="500 ml")],
        [KeyboardButton(text="750 ml"), KeyboardButton(text="1000 ml")],
        [KeyboardButton(text=t("enter_custom_amount", lang))],
        [KeyboardButton(text=t("cancel_action", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t("menu_log_meal", lang)), KeyboardButton(text=t("menu_log_water", lang))],
        [KeyboardButton(text=t("menu_stats", lang)), KeyboardButton(text=t("menu_settings", lang))],
        [KeyboardButton(text=t("menu_help", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_settings_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t("edit_profile", lang)), KeyboardButton(text=t("edit_reminders", lang))],
        [KeyboardButton(text=t("change_language", lang)), KeyboardButton(text=t("edit_body_fat", lang))],
        [KeyboardButton(text=t("back_to_settings", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_profile_edit_keyboard(lang: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t("edit_name", lang)), KeyboardButton(text=t("edit_age", lang))],
        [KeyboardButton(text=t("edit_height", lang)), KeyboardButton(text=t("edit_weight", lang))],
        [KeyboardButton(text=t("back_to_settings", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True) 