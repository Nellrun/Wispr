import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from .utils.logger import logger
from .config import config
from .database.db import db
from .middlewares.access import AccessMiddleware
from .routers import admin, settings, chats, images


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
        BotCommand(command="image", description="Создать изображение по описанию"),
    ]
    
    await bot.set_my_commands(commands)


async def start_bot() -> None:
    """Initialize and start the bot."""
    # Initialize storage and dispatcher
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    bot = Bot(token=config.bot_token)
    
    # Register middlewares
    dp.message.middleware.register(AccessMiddleware())
    dp.callback_query.middleware.register(AccessMiddleware())
    
    # Register routers
    dp.include_router(admin.router)
    dp.include_router(settings.router)
    dp.include_router(chats.router)
    dp.include_router(images.router)
    
    # Register basic commands
    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        """Handle /start command."""
        await message.answer(
            f"👋 Добро пожаловать в Wispr Bot!\n\n"
            f"Я Telegram бот, который позволяет общаться с моделями OpenAI.\n\n"
            f"Используйте /help чтобы увидеть доступные команды."
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        """Handle /help command."""
        help_text = (
            "🔍 Доступные команды:\n\n"
            "/newchat - Создать новый чат\n"
            "/chats - Показать все чаты\n"
            "/currentchat - Информация о текущем чате\n"
            "/clear_history - Очистить историю текущего чата\n"
            "/exit - Выйти из текущего чата\n"
            "/image - Создать изображение по описанию\n"
            "/settings - Настройки\n"
            "/help - Показать справку\n\n"
            "Просто отправьте сообщение, чтобы начать общение!"
        )
        await message.answer(help_text)
    
    # Connect to database
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return
    
    # Set commands
    await set_commands(bot)
    
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        logger.info("Stopping bot...")
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(start_bot()) 