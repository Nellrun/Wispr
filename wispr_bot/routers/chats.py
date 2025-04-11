from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from typing import Optional, Dict, Set
import asyncio

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..models.chat import Chat
from ..config import config
from ..services.openai_service import OpenAIService


# Create router
router = Router()


# Chat states
class ChatStates(StatesGroup):
    """States for chat operations."""
    waiting_for_title = State()
    in_chat = State()  # When user is actively in a chat


# Session storage for active chats
# This is a simple in-memory storage, which will be reset on bot restart
active_chats: Dict[int, int] = {}  # user_id -> chat_id

# Set для отслеживания пользователей, которые ожидают ответа от OpenAI
# Используется для предотвращения обработки новых сообщений до завершения предыдущего запроса
processing_users: Set[int] = set()


@router.message(Command("newchat"))
async def new_chat_command(message: Message, state: FSMContext, user: User) -> None:
    """Start creating a new chat."""
    await message.answer(
        "🆕 Создание нового чата\n\n"
        "Пожалуйста, введите название для вашего нового чата:"
    )
    
    # Set state to waiting for title
    await state.set_state(ChatStates.waiting_for_title)


@router.message(StateFilter(ChatStates.waiting_for_title), Command("cancel"))
async def cancel_new_chat(message: Message, state: FSMContext) -> None:
    """Cancel new chat creation."""
    await state.clear()
    await message.answer("❌ Создание нового чата отменено")


@router.message(StateFilter(ChatStates.waiting_for_title))
async def process_new_chat_title(message: Message, state: FSMContext, user: User) -> None:
    """Process the title for a new chat."""
    # Get title from message
    title = message.text.strip()
    
    # Get user's preferred model or use default
    model = user.preferred_model or config.default_model
    
    # Create new chat
    chat = await db.create_chat(
        user_id=user.telegram_id,
        title=title,
        model=model
    )
    
    # Set active chat for user
    active_chats[user.telegram_id] = chat.id
    
    # Set state to in chat
    await state.set_state(ChatStates.in_chat)
    await state.update_data(chat_id=chat.id)
    
    await message.answer(
        f"✅ Создан новый чат: \"{title}\"\n\n"
        f"Теперь вы общаетесь с моделью {model}.\n"
        f"Отправьте любое сообщение, чтобы начать разговор."
    )
    logger.info(f"User {user.telegram_id} created new chat {chat.id}: {title}")


@router.message(Command("chats"))
async def list_chats(message: Message, user: User) -> None:
    """List user's chats."""
    # Get user's chats
    chats = await db.get_user_chats(user.telegram_id)
    
    if not chats:
        await message.answer(
            "📝 У вас еще нет чатов.\n\n"
            "Используйте /newchat, чтобы создать первый чат."
        )
        return
    
    # Build keyboard with chats
    builder = InlineKeyboardBuilder()
    
    for chat in chats[:10]:  # Limit to first 10 chats to avoid huge keyboards
        builder.button(
            text=f"{chat['title']} ({chat['model']})",
            callback_data=f"chat:{chat['id']}"
        )
    
    # Add a button for more chats if needed
    if len(chats) > 10:
        builder.button(
            text="Показать больше...",
            callback_data="chats:more"
        )
    
    builder.adjust(1)  # One button per row
    
    await message.answer(
        f"📝 Ваши чаты ({len(chats)}):\n\n"
        f"Нажмите на чат, чтобы продолжить разговор:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("chat:"))
async def select_chat(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    """Select a chat to continue."""
    # Get chat id from callback data
    chat_id = int(callback.data.split(":", 1)[1])
    
    # Get chat from database
    chat = await db.get_chat(chat_id)
    
    if not chat or chat.user_id != user.telegram_id:
        await callback.answer("❌ Чат не найден или отказано в доступе", show_alert=True)
        return
    
    # Set active chat for user
    active_chats[user.telegram_id] = chat.id
    
    # Set state to in chat
    await state.set_state(ChatStates.in_chat)
    await state.update_data(chat_id=chat.id)
    
    await callback.answer()
    await callback.message.answer(
        f"✅ Переключено на чат: \"{chat.title}\"\n\n"
        f"Теперь вы общаетесь с моделью {chat.model}.\n"
        f"Отправьте любое сообщение, чтобы продолжить разговор."
    )
    logger.info(f"User {user.telegram_id} switched to chat {chat.id}")


@router.message(Command("deletechat"))
async def delete_chat_command(message: Message, user: User) -> None:
    """Start the process to delete a chat."""
    # Get user's chats
    chats = await db.get_user_chats(user.telegram_id)
    
    if not chats:
        await message.answer("📝 У вас нет чатов для удаления.")
        return
    
    # Build keyboard with chats to delete
    builder = InlineKeyboardBuilder()
    
    for chat in chats[:10]:  # Limit to first 10 chats
        builder.button(
            text=f"🗑 {chat['title']}",
            callback_data=f"delete_chat:{chat['id']}"
        )
    
    builder.button(
        text="❌ Отмена",
        callback_data="delete_chat:cancel"
    )
    
    builder.adjust(1)  # One button per row
    
    await message.answer(
        "🗑 Выберите чат для удаления:\n\n"
        "⚠️ Это действие нельзя отменить!",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("delete_chat:"))
async def delete_chat_callback(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    """Handle chat deletion."""
    # Get chat id from callback data
    chat_id_str = callback.data.split(":", 1)[1]
    
    if chat_id_str == "cancel":
        await callback.answer("Операция отменена")
        await callback.message.edit_text("❌ Удаление чата отменено")
        return
    
    chat_id = int(chat_id_str)
    
    # Delete chat
    success = await db.delete_chat(chat_id)
    
    if success:
        # If deleted chat was active, clear the active chat
        if active_chats.get(user.telegram_id) == chat_id:
            active_chats.pop(user.telegram_id, None)
            # Also clear state if we're in this chat
            current_data = await state.get_data()
            if current_data.get('chat_id') == chat_id:
                await state.clear()
        
        await callback.answer("Чат успешно удален")
        await callback.message.edit_text("✅ Чат успешно удален")
        logger.info(f"User {user.telegram_id} deleted chat {chat_id}")
    else:
        await callback.answer("Не удалось удалить чат", show_alert=True)
        await callback.message.edit_text("❌ Не удалось удалить чат")


@router.message(Command("currentchat"))
async def current_chat_info(message: Message, user: User, state: FSMContext) -> None:
    """Show information about the current active chat."""
    # Check if user has an active chat
    chat_id = active_chats.get(user.telegram_id)
    
    if not chat_id:
        await message.answer(
            "❓ У вас нет активного чата.\n\n"
            "Используйте /newchat, чтобы создать новый чат, или /chats, чтобы выбрать существующий."
        )
        return
    
    # Get chat from database
    chat = await db.get_chat(chat_id)
    
    if not chat:
        # Chat not found - maybe it was deleted
        active_chats.pop(user.telegram_id, None)
        await state.clear()
        await message.answer(
            "❓ Ваш активный чат не найден.\n\n"
            "Используйте /newchat, чтобы создать новый чат, или /chats, чтобы выбрать существующий."
        )
        return
    
    # Show chat info
    msg_count = len(chat.messages)
    await message.answer(
        f"📝 Текущий чат: \"{chat.title}\"\n\n"
        f"• Модель: {chat.model}\n"
        f"• Создан: {chat.created_at.strftime('%Y-%m-%d')}\n"
        f"• Сообщений: {msg_count}\n\n"
        f"Используйте /chats, чтобы переключиться на другой чат."
    )


@router.message(StateFilter(ChatStates.in_chat))
async def process_chat_message(message: Message, state: FSMContext, user: User) -> None:
    """Process a message in an active chat."""
    # Если сообщение начинается с "/", это команда, пропускаем обработку
    if message.text.startswith('/'):
        return
    
    # Проверяем, не обрабатывается ли уже запрос от этого пользователя
    if user.telegram_id in processing_users:
        await message.answer(
            "⏳ Ваш предыдущий запрос еще обрабатывается. Пожалуйста, подождите."
        )
        return
    
    # Добавляем пользователя в множество обрабатываемых
    processing_users.add(user.telegram_id)
    
    try:
        # Get chat id from state
        data = await state.get_data()
        chat_id = data.get('chat_id')
        
        # If no chat id in state, try to get from active chats
        if not chat_id:
            chat_id = active_chats.get(user.telegram_id)
            
            # If still no chat id, create a new chat
            if not chat_id:
                await message.answer(
                    "❓ У вас нет активного чата.\n\n"
                    "Я создам новый для вас.",
                )
                # Create new chat with default title
                chat = await db.create_chat(
                    user_id=user.telegram_id,
                    title=f"Чат {message.date.strftime('%Y-%m-%d %H:%M')}",
                    model=user.preferred_model or config.default_model
                )
                chat_id = chat.id
                # Set active chat and update state
                active_chats[user.telegram_id] = chat_id
                await state.update_data(chat_id=chat_id)
        
        # Get chat from database
        chat = await db.get_chat(chat_id)
        
        if not chat:
            # Chat not found - maybe it was deleted
            active_chats.pop(user.telegram_id, None)
            await state.clear()
            await message.answer(
                "❓ Ваш активный чат не найден.\n\n"
                "Я создам новый для вас."
            )
            # Create new chat with default title
            chat = await db.create_chat(
                user_id=user.telegram_id,
                title=f"Чат {message.date.strftime('%Y-%m-%d %H:%M')}",
                model=user.preferred_model or config.default_model
            )
            chat_id = chat.id
            # Set active chat and update state
            active_chats[user.telegram_id] = chat_id
            await state.set_state(ChatStates.in_chat)
            await state.update_data(chat_id=chat_id)
        
        # Сохраняем текущее сообщение пользователя, чтобы знать, на какой запрос отвечаем
        current_user_message = message.text
        
        # Add user message to chat
        await db.add_message(chat_id, "user", current_user_message)
        
        # Отправляем временное сообщение "Генерация ответа..." и сохраняем его ID для обновления
        temp_message = await message.answer("⏳ Генерация ответа...")
        
        # Send "typing" action
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Process with OpenAI
        openai_service = OpenAIService(user.openai_api_key if user.has_custom_api_key else None)
        
        # Get messages context from chat
        context_messages = chat.get_context_messages(current_user_message)
        
        # Проверяем, что у нас есть сообщения в контексте
        if not context_messages:
            await message.bot.edit_message_text(
                "⚠️ Ошибка: Не удалось сформировать контекст сообщений для запроса.",
                chat_id=message.chat.id,
                message_id=temp_message.message_id
            )
            return
        
        # Call OpenAI API
        try:
            # Запускаем периодический запрос "typing"
            typing_task = asyncio.create_task(
                keep_typing(message.bot, message.chat.id)
            )
            
            # Используем потоковую генерацию ответа вместо обычной
            final_response = ""
            update_counter = 0
            update_interval = 20  # Обновляем сообщение каждые 5 токенов, чтобы не перегружать API Telegram
            
            async for response_chunk in openai_service.generate_response_stream(
                messages=context_messages,
                model=chat.model
            ):
                # Если ответ начинается с ошибки, прерываем обработку
                if response_chunk.startswith("⚠️ Ошибка"):
                    final_response = response_chunk
                    break
                
                # Обновляем сообщение с частичным ответом только через некоторые интервалы
                # чтобы не делать слишком много запросов к API Telegram
                update_counter += 1
                if update_counter % update_interval == 0:
                    try:
                        # В некоторых случаях ответ может быть очень длинным и не поместиться в одно сообщение
                        if len(response_chunk) <= 4096:  # Telegram ограничение на длину сообщения
                            await message.bot.edit_message_text(
                                response_chunk + " ⏳",  # Добавляем индикатор, что генерация продолжается
                                chat_id=message.chat.id,
                                message_id=temp_message.message_id
                            )
                    except Exception as e:
                        logger.warning(f"Error updating partial response: {e}")
                
                # Сохраняем последний чанк как финальный ответ
                final_response = response_chunk
            
            # Останавливаем периодический запрос "typing"
            typing_task.cancel()
            
            # Проверка финального ответа
            if not final_response:
                final_response = "⚠️ Пустой ответ от API"
                
            # Сохраняем финальный ответ в базу
            await db.add_message(chat_id, "assistant", final_response)
            
            # Обновляем сообщение с финальным ответом (больше без индикатора загрузки)
            try:
                # Если ответ слишком длинный, разбиваем его на части
                if len(final_response) > 4096:
                    # Сначала удаляем временное сообщение
                    await message.bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=temp_message.message_id
                    )
                    
                    # Отправляем ответ частями
                    for i in range(0, len(final_response), 4000):
                        part = final_response[i:i+4000]
                        await message.answer(part)
                else:
                    await message.bot.edit_message_text(
                        final_response,
                        chat_id=message.chat.id,
                        message_id=temp_message.message_id
                    )
            except Exception as e:
                logger.error(f"Error sending final response: {e}")
                await message.answer(f"⚠️ Ошибка при отправке ответа: {e}")
                
        except Exception as e:
            error_message = f"⚠️ Ошибка при генерации ответа: {str(e)}"
            logger.error(f"Error generating response: {e}")
            
            # Обновляем временное сообщение с ошибкой
            await message.bot.edit_message_text(
                error_message,
                chat_id=message.chat.id,
                message_id=temp_message.message_id
            )
            
            await db.add_message(chat_id, "assistant", error_message)
    
    finally:
        # Удаляем пользователя из множества обрабатываемых в любом случае
        processing_users.discard(user.telegram_id)


async def keep_typing(bot: Bot, chat_id: int, interval: float = 4.0):
    """Keep sending typing action to keep the user informed about ongoing processing."""
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        # Нормальное завершение задачи
        pass
    except Exception as e:
        logger.error(f"Error in keep_typing: {e}")


@router.message(Command("exit"))
async def exit_chat(message: Message, state: FSMContext, user: User) -> None:
    """Exit current chat."""
    # Clear active chat
    active_chats.pop(user.telegram_id, None)
    
    # Clear state
    await state.clear()
    
    await message.answer(
        "✅ Вы вышли из текущего чата.\n\n"
        "Используйте /chats, чтобы выбрать чат, или /newchat, чтобы создать новый."
    )
    
    
@router.message(Command("clear_history"))
async def clear_chat_history(message: Message, state: FSMContext, user: User) -> None:
    """Clear history of the current chat."""
    # Get chat id from active chats
    chat_id = active_chats.get(user.telegram_id)
    
    if not chat_id:
        await message.answer(
            "❓ У вас нет активного чата для очистки истории.\n\n"
            "Используйте /newchat, чтобы создать новый чат, или /chats, чтобы выбрать существующий."
        )
        return
    
    # Get chat from database
    chat = await db.get_chat(chat_id)
    
    if not chat:
        await message.answer(
            "❓ Ваш активный чат не найден.\n\n"
            "Используйте /newchat, чтобы создать новый чат, или /chats, чтобы выбрать существующий."
        )
        active_chats.pop(user.telegram_id, None)
        await state.clear()
        return
        
    # Создаем новый чат с тем же названием и моделью, но без истории
    new_chat = await db.create_chat(
        user_id=user.telegram_id,
        title=f"{chat.title} (очищен)",
        model=chat.model,
        system_prompt=chat.system_prompt
    )
    
    # Обновляем активный чат
    active_chats[user.telegram_id] = new_chat.id
    await state.update_data(chat_id=new_chat.id)
    
    await message.answer(
        f"✅ История чата очищена. Создан новый чат \"{new_chat.title}\".\n\n"
        f"Вы можете начать новый разговор с моделью {new_chat.model}."
    )
    logger.info(f"User {user.telegram_id} cleared chat history. Created new chat {new_chat.id}") 