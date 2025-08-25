from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime
import pytz

from ..utils.states import UserStates
from ..utils.keyboards import get_language_keyboard, get_main_keyboard
from ..database.db import get_user_ref, set_user_language
from ..locales.translations import t

async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        # Existing user
        lang = user_doc.to_dict().get('language', 'en')
        await message.answer(
            t("welcome_back", lang),
            reply_markup=get_main_keyboard(lang)
        )
        return

    # New user - start registration
    await message.answer(
        t("intro", "en"),
        reply_markup=get_language_keyboard()
    )
    await state.set_state(UserStates.SELECTING_LANGUAGE)

async def process_language_selection(message: types.Message, state: FSMContext):
    """Handle language selection"""
    if message.text in ["🇺🇸 English", "🇷🇺 Русский", "🇺🇿 O'zbek"]:
        lang = "en" if "English" in message.text else "ru" if "Русский" in message.text else "uz"
        user_id = message.from_user.id
        
        # Create new user
        user_ref = get_user_ref(user_id)
        user_ref.set({
            'user_id': user_id,
            'language': lang,
            'created_at': datetime.now(pytz.UTC),
            'last_active': datetime.now(pytz.UTC)
        })
        
        await message.answer(
            t("language_selected", lang),
            reply_markup=get_main_keyboard(lang)
        )
        await state.clear()
    else:
        await message.answer(t("select_language", "en"))

def register_start_handlers(dp: Dispatcher):
    """Register all start-related handlers"""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(process_language_selection, UserStates.SELECTING_LANGUAGE) 