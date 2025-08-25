from aiogram.fsm.state import StatesGroup, State

class UserStates(StatesGroup):
    # Registration states
    SELECTING_LANGUAGE = State()
    ENTERING_NAME = State()
    ENTERING_AGE = State()
    ENTERING_HEIGHT = State()
    ENTERING_WEIGHT = State()
    SELECTING_GENDER = State()
    SELECTING_TIMEZONE = State()
    SELECTING_GOAL = State()
    SELECTING_ACTIVITY = State()
    ENTERING_BODY_FAT = State()
    
    # Logging states
    WATER_AMOUNT = State()
    CUSTOM_WATER_AMOUNT = State()
    MEAL_TYPE = State()
    MEAL_DESCRIPTION = State()
    
    # Settings states
    SETTINGS_MENU = State()
    UPDATING_LANGUAGE = State()
    UPDATING_REMINDERS = State()
    UPDATING_BODY_FAT = State()
    UPDATING_PROFILE = State()
    CONFIRMING_ACTION = State() 