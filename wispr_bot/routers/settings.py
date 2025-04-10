from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..config import config
from ..services.openai_service import OpenAIService


# Create router
router = Router()


# FSM States
class SettingsStates(StatesGroup):
    """States for settings operations."""
    waiting_for_api_key = State()
    waiting_for_model = State()


@router.message(Command("settings"))
async def settings_command(message: Message, user: User) -> None:
    """Show user settings."""
    # Format settings message
    api_key_status = "✅ Установлен" if user.has_custom_api_key else "❌ Не установлен"
    preferred_model = user.preferred_model or config.default_model
    
    settings_text = (
        f"⚙️ Настройки пользователя\n\n"
        f"• API ключ: {api_key_status}\n"
        f"• Предпочитаемая модель: {preferred_model}\n\n"
        f"Команды:\n"
        f"/setapikey - Установить свой API ключ OpenAI\n"
        f"/removeapikey - Удалить свой API ключ\n"
        f"/setmodel - Выбрать предпочитаемую модель ChatGPT"
    )
    
    await message.answer(settings_text)


@router.message(Command("setapikey"))
async def set_api_key_command(message: Message, state: FSMContext) -> None:
    """Start the process to set user's OpenAI API key."""
    await message.answer(
        "🔑 Пожалуйста, введите ваш API ключ OpenAI.\n\n"
        "Он будет использоваться для ваших запросов вместо ключа бота по умолчанию.\n"
        "Вы можете отменить эту операцию командой /cancel"
    )
    
    # Set state to waiting for API key
    await state.set_state(SettingsStates.waiting_for_api_key)


@router.message(StateFilter(SettingsStates.waiting_for_api_key), Command("cancel"))
async def cancel_api_key(message: Message, state: FSMContext) -> None:
    """Cancel the API key setting process."""
    await state.clear()
    await message.answer("❌ Установка API ключа отменена")


@router.message(StateFilter(SettingsStates.waiting_for_api_key))
async def process_api_key(message: Message, state: FSMContext, user: User) -> None:
    """Process the API key received from the user."""
    # Get API key from message
    api_key = message.text.strip()
    
    # Create OpenAI service to validate the key
    openai_service = OpenAIService()
    is_valid = await openai_service.validate_api_key(api_key)
    
    if not is_valid:
        await message.answer(
            "❌ Недействительный API ключ. Пожалуйста, попробуйте еще раз с действующим API ключом OpenAI или /cancel"
        )
        return
    
    # Update user's API key in database
    await db.update_user_api_key(user.telegram_id, api_key)
    
    # Clear state
    await state.clear()
    
    await message.answer("✅ Ваш API ключ OpenAI успешно сохранен")
    logger.info(f"User {user.telegram_id} updated their API key")


@router.message(Command("removeapikey"))
async def remove_api_key(message: Message, user: User) -> None:
    """Remove user's custom API key."""
    if not user.has_custom_api_key:
        await message.answer("❓ У вас не установлен собственный API ключ")
        return
    
    # Remove API key
    await db.update_user_api_key(user.telegram_id, None)
    
    await message.answer(
        "🗑 Ваш API ключ удален. "
        "Бот будет использовать API ключ по умолчанию для ваших запросов."
    )
    logger.info(f"User {user.telegram_id} removed their API key")


@router.message(Command("setmodel"))
async def set_model_command(message: Message, state: FSMContext) -> None:
    """Start the process to set user's preferred model."""
    models_list = "\n".join([f"• {model}" for model in config.available_models])
    
    await message.answer(
        f"🤖 Пожалуйста, выберите предпочитаемую модель ChatGPT:\n\n{models_list}\n\n"
        f"Просто отправьте название модели (например, {config.default_model}).\n"
        f"Вы можете отменить эту операцию командой /cancel"
    )
    
    # Set state to waiting for model
    await state.set_state(SettingsStates.waiting_for_model)


@router.message(StateFilter(SettingsStates.waiting_for_model), Command("cancel"))
async def cancel_model_selection(message: Message, state: FSMContext) -> None:
    """Cancel the model setting process."""
    await state.clear()
    await message.answer("❌ Выбор модели отменен")


@router.message(StateFilter(SettingsStates.waiting_for_model))
async def process_model_selection(message: Message, state: FSMContext, user: User) -> None:
    """Process the model selection received from the user."""
    # Get model from message
    selected_model = message.text.strip()
    
    # Validate model
    if selected_model not in config.available_models:
        models_list = ", ".join(config.available_models)
        await message.answer(
            f"❌ Неверная модель. Пожалуйста, выберите из: {models_list} или /cancel"
        )
        return
    
    # Update user's preferred model in database
    await db.update_user_preferred_model(user.telegram_id, selected_model)
    
    # Clear state
    await state.clear()
    
    await message.answer(f"✅ Ваша предпочитаемая модель установлена на {selected_model}")
    logger.info(f"User {user.telegram_id} updated their preferred model to {selected_model}") 