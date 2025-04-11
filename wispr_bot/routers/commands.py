from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.types.bot_command import BotCommand
from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import os
import uuid
from typing import List, Dict, Optional

from openai import AsyncOpenAI
from openai.types.images_response import ImagesResponse

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..config import config
from ..services.openai_service import OpenAIService
from ..utils.chat_manager import ChatManager


# Create router
router = Router()


async def set_commands(bot: Bot) -> None:
    """Set bot commands for menu button."""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="newchat", description="Создать новый чат"),
        BotCommand(command="chats", description="Показать все чаты"),
        BotCommand(command="currentchat", description="Информация о текущем чате"),
        BotCommand(command="clear_history", description="Очистить историю текущего чата"),
        BotCommand(command="exit", description="Выйти из текущего чата"),
        BotCommand(command="image", description="Создать изображение с DALL-E 3"),
    ]
    
    await bot.set_my_commands(commands)


@router.message(Command("start"))
async def start_command(message: Message, user: User) -> None:
    """Send a message when the command /start is issued."""
    await message.answer(
        f"👋 Добро пожаловать в Wispr Bot, {user.username}!\n\n"
        f"Я Telegram бот, который позволяет общаться с моделями OpenAI.\n\n"
        f"Используйте /help чтобы увидеть доступные команды."
    )


@router.message(Command("help"))
async def help_command(message: Message, user: User) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
🔍 *Доступные команды*

*Основные команды:*
• /newchat - Создать новый чат
• /chats - Показать все чаты
• /currentchat - Информация о текущем чате
• /clear_history - Очистить историю текущего чата
• /exit - Выйти из текущего чата

*Генерация изображений:*
• /image [описание] - Создать изображение с DALL-E 3
  *Пример:* `/image космический корабль в стиле киберпанк`

*Настройки:*
• /settings - Настройки бота
• /setapikey - Установить свой API ключ OpenAI
• /removeapikey - Удалить свой API ключ
• /setmodel - Выбрать модель по умолчанию

*Использование бота:*
Просто отправьте сообщение, чтобы начать общение с выбранной моделью OpenAI.
Все сообщения сохраняются в контексте текущего чата.
"""
    await message.answer(help_text, parse_mode='Markdown')


@router.message(Command("image"))
async def image_command(message: Message, user: User) -> None:
    """Generate an image using DALL-E 3."""
    # Получаем аргументы команды (описание изображения)
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        await message.answer(
            "Пожалуйста, укажите описание изображения.\n"
            "Пример: `/image космический корабль в стиле киберпанк`",
            parse_mode="Markdown"
        )
        return
    
    prompt = command_parts[1]
    
    # Проверяем наличие API ключа
    api_key = user.openai_api_key if user.has_custom_api_key else config.openai_api_key
    
    if not api_key:
        await message.answer(
            "⚠️ API ключ OpenAI не настроен. "
            "Используйте /setapikey для установки ключа, либо обратитесь к администратору."
        )
        return
    
    # Отправляем сообщение о начале генерации
    status_message = await message.answer("🖌 Генерация изображения...")
    
    try:
        # Создаем клиент OpenAI
        client = AsyncOpenAI(api_key=api_key)
        
        # Отправляем запрос на генерацию изображения
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        # Получаем URL сгенерированного изображения
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        # Отправляем изображение пользователю
        await message.bot.edit_message_text(
            "✅ Изображение сгенерировано! Отправляю...",
            chat_id=message.chat.id,
            message_id=status_message.message_id
        )
        
        # Отправляем изображение по URL
        await message.answer_photo(
            photo=image_url,
            caption=f"🖼 *Сгенерировано изображение*\n\n"
                   f"*Запрос:* {prompt}\n\n"
                   f"*Доработанный запрос DALL-E:*\n{revised_prompt}",
            parse_mode="Markdown"
        )
        
        # Удаляем статусное сообщение
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=status_message.message_id
        )
        
        logger.info(f"User {user.telegram_id} generated image with prompt: {prompt}")
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        await message.bot.edit_message_text(
            f"⚠️ Ошибка при генерации изображения: {str(e)}",
            chat_id=message.chat.id,
            message_id=status_message.message_id
        )


def register_commands(application: Bot) -> None:
    """Register all command handlers in the application."""
    # Command list can be registered here if using a different framework
    pass
