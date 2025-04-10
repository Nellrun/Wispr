from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..config import config


class AccessMiddleware(BaseMiddleware):
    """Middleware to check if a user is allowed to use the bot."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Check if user is allowed to use the bot."""
        # Get user from update
        if isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
        else:
            # Allow non-user updates to pass through
            return await handler(event, data)
        
        # Get user from database
        user = await db.get_user(user_id)
        
        # If user does not exist, create new user
        if not user:
            user = User(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_allowed=user_id in config.admin_user_ids  # Auto-allow admins
            )
            await db.create_or_update_user(user)
        else:
            # Update user info
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            await db.create_or_update_user(user)
        
        # Add user to data dict for handlers
        data["user"] = user
        
        # Check if user is allowed to use the bot
        if user.is_allowed or user_id in config.admin_user_ids:
            return await handler(event, data)
        
        # If user is not allowed, send message and stop processing
        if isinstance(event, Message):
            await event.answer(
                "⚠️ У вас нет доступа к этому боту. Пожалуйста, обратитесь к администратору."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "⚠️ У вас нет доступа к этому боту.",
                show_alert=True
            )
        
        logger.warning(f"Unauthorized access attempt by user {user_id} ({username})")
        return None 