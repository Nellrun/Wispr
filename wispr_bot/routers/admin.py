from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..config import config


# Create router
router = Router()


# Admin-only filter
def is_admin(message: Message) -> bool:
    """Check if user is an admin."""
    return message.from_user.id in config.admin_user_ids


@router.message(Command("admin"), is_admin)
async def admin_panel(message: Message, user: User) -> None:
    """Show admin panel."""
    commands = [
        "/allow <user_id> - Разрешить пользователю использовать бота",
        "/disallow <user_id> - Запретить пользователю использовать бота",
        "/list_users - Список всех пользователей",
        "/stats - Показать статистику бота"
    ]
    
    await message.answer(
        f"👑 Панель администратора\n\n"
        f"Доступные команды:\n" + "\n".join(commands)
    )


@router.message(Command("allow"), is_admin)
async def allow_user(message: Message, command: CommandObject) -> None:
    """Allow a user to use the bot."""
    # Check if user_id is provided
    if not command.args:
        await message.answer("⚠️ Пожалуйста, укажите ID пользователя: /allow <user_id>")
        return
    
    try:
        user_id = int(command.args)
        
        # Get user from database
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer(f"⚠️ Пользователь с ID {user_id} не найден в базе данных")
            return
        
        # Update user's allowed status
        await db.update_user_allowed_status(user_id, True)
        
        await message.answer(f"✅ Пользователю {user.full_name} ({user_id}) предоставлен доступ к боту")
        logger.info(f"User {user_id} allowed by admin {message.from_user.id}")
        
    except ValueError:
        await message.answer("⚠️ Неверный ID пользователя. Пожалуйста, укажите корректный числовой ID")


@router.message(Command("disallow"), is_admin)
async def disallow_user(message: Message, command: CommandObject) -> None:
    """Disallow a user from using the bot."""
    # Check if user_id is provided
    if not command.args:
        await message.answer("⚠️ Пожалуйста, укажите ID пользователя: /disallow <user_id>")
        return
    
    try:
        user_id = int(command.args)
        
        # Check if attempting to disallow an admin
        if user_id in config.admin_user_ids:
            await message.answer("⚠️ Невозможно запретить доступ администратору")
            return
        
        # Get user from database
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer(f"⚠️ Пользователь с ID {user_id} не найден в базе данных")
            return
        
        # Update user's allowed status
        await db.update_user_allowed_status(user_id, False)
        
        await message.answer(f"❌ Пользователю {user.full_name} ({user_id}) запрещен доступ к боту")
        logger.info(f"User {user_id} disallowed by admin {message.from_user.id}")
        
    except ValueError:
        await message.answer("⚠️ Неверный ID пользователя. Пожалуйста, укажите корректный числовой ID")


@router.message(Command("list_users"), is_admin)
async def list_users(message: Message) -> None:
    """List all users."""
    # Get all allowed users
    allowed_users = await db.get_allowed_users()
    
    if not allowed_users:
        await message.answer("📝 Разрешенных пользователей не найдено")
        return
    
    # Format user list
    user_list = "\n".join([
        f"• {user.full_name} (ID: {user.telegram_id})"
        f"{' [Свой API ключ]' if user.has_custom_api_key else ''}"
        for user in allowed_users
    ])
    
    await message.answer(
        f"📝 Разрешенные пользователи ({len(allowed_users)}):\n\n{user_list}"
    )


@router.message(Command("stats"), is_admin)
async def stats(message: Message) -> None:
    """Show bot statistics."""
    # Get all users
    all_users = await db.get_allowed_users()
    
    await message.answer(
        f"📊 Статистика бота\n\n"
        f"Всего разрешенных пользователей: {len(all_users)}\n"
        f"Пользователей со своим API ключом: {sum(1 for user in all_users if user.has_custom_api_key)}"
    ) 