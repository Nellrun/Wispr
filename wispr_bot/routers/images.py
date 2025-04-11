from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import aiohttp
import asyncio
import tempfile
import uuid

from ..utils.logger import logger
from ..database.db import db
from ..models.user import User
from ..services.openai_service import OpenAIService

# Create router
router = Router()

# Image generation states
class ImageGenStates(StatesGroup):
    """States for image generation operations."""
    waiting_for_prompt = State()

# Temporary storage for downloaded images
TEMP_DIR = os.path.join(tempfile.gettempdir(), "wispr_bot_images")
os.makedirs(TEMP_DIR, exist_ok=True)

@router.message(Command("image"))
async def image_command(message: Message, state: FSMContext, user: User, command: CommandObject) -> None:
    """Generate an image using DALL-E-3."""
    # Check if prompt is provided in the command
    if command.args:
        # Prompt is provided directly in the command
        await generate_image(message, user, command.args)
    else:
        # Ask for a prompt
        await message.answer(
            "🖼️ *Генерация изображения*\n\n"
            "Пожалуйста, опишите изображение, которое вы хотите сгенерировать:",
            parse_mode="Markdown"
        )
        await state.set_state(ImageGenStates.waiting_for_prompt)

@router.message(StateFilter(ImageGenStates.waiting_for_prompt), Command("cancel"))
async def cancel_image_gen(message: Message, state: FSMContext) -> None:
    """Cancel image generation."""
    await state.clear()
    await message.answer("❌ Генерация изображения отменена", parse_mode="Markdown")

@router.message(StateFilter(ImageGenStates.waiting_for_prompt))
async def process_image_prompt(message: Message, state: FSMContext, user: User) -> None:
    """Process the prompt for image generation."""
    # Clear the state first
    await state.clear()
    
    # Get prompt from message
    prompt = message.text.strip()
    
    # Generate image
    await generate_image(message, user, prompt)

async def generate_image(message: Message, user: User, prompt: str) -> None:
    """Generate an image using DALL-E-3."""
    # Send typing action to indicate processing
    await message.bot.send_chat_action(message.chat.id, "upload_photo")
    
    # Send waiting message
    waiting_msg = await message.answer(
        "⏳ *Генерация изображения*...\n"
        "Это может занять до 30 секунд.",
        parse_mode="Markdown"
    )
    
    # Create OpenAI service
    openai_service = OpenAIService(user.openai_api_key if user.has_custom_api_key else None)
    
    # Generate image
    result = await openai_service.generate_image(prompt)
    
    if result["success"]:
        # Download the image
        image_url = result["url"]
        revised_prompt = result.get("revised_prompt", prompt)
        
        try:
            # Generate a unique filename
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(TEMP_DIR, filename)
            
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        with open(filepath, "wb") as f:
                            f.write(await response.read())
                    else:
                        raise Exception(f"Failed to download image: {response.status}")
            
            # Send the image
            photo = FSInputFile(filepath)
            
            # Delete waiting message
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id
            )
            
            # Send image with caption
            await message.answer_photo(
                photo,
                caption=(
                    f"🖼️ *Изображение сгенерировано*\n\n"
                    f"*Запрос:* {prompt}\n"
                    f"{f'*Улучшенный запрос:* {revised_prompt}' if revised_prompt != prompt else ''}"
                ),
                parse_mode="Markdown"
            )
            
            # Clean up the file
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Error deleting temporary file: {e}")
                
            logger.info(f"User {user.telegram_id} generated image with prompt: {prompt}")
            
        except Exception as e:
            logger.error(f"Error downloading or sending image: {e}")
            
            # Delete waiting message
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id
            )
            
            # Send image URL instead
            await message.answer(
                f"🖼️ *Изображение сгенерировано*\n\n"
                f"*Запрос:* {prompt}\n"
                f"{f'*Улучшенный запрос:* {revised_prompt}' if revised_prompt != prompt else ''}\n\n"
                f"[Ссылка на изображение]({image_url})",
                parse_mode="Markdown"
            )
    else:
        # Error occurred
        error_message = result["error"]
        await message.bot.edit_message_text(
            f"⚠️ *Ошибка при генерации изображения*: {error_message}",
            chat_id=message.chat.id,
            message_id=waiting_msg.message_id,
            parse_mode="Markdown"
        )
        logger.error(f"Image generation error for user {user.telegram_id}: {error_message}") 