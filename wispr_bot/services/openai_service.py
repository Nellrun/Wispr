import asyncio
from typing import List, Dict, Optional, AsyncGenerator
import openai
from openai import AsyncOpenAI

from ..utils.logger import logger
from ..config import config


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client with API key."""
        self.api_key = api_key or config.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    def update_api_key(self, api_key: str) -> None:
        """Update API key and reinitialize client."""
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-3.5-turbo"
    ) -> str:
        """Generate response from OpenAI API."""
        try:
            # Проверка на пустой массив сообщений
            if not messages:
                logger.error("Empty messages array provided to OpenAI API")
                return "⚠️ Ошибка: Пустой массив сообщений для API"
                
            # Validate model
            if model not in config.available_models:
                model = config.default_model
                logger.warning(f"Invalid model requested. Using default: {model}")
            
            # Проверяем каждое сообщение на корректность
            for i, msg in enumerate(messages):
                if 'role' not in msg or 'content' not in msg:
                    logger.error(f"Invalid message format at index {i}: {msg}")
                    return "⚠️ Ошибка: Некорректный формат сообщения"
                
                if not msg['content']:
                    logger.warning(f"Empty content in message at index {i}")
                    messages[i]['content'] = " "  # Заменяем пустую строку на пробел
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Проверяем, что есть ответ
            if not response.choices or len(response.choices) == 0:
                logger.error("OpenAI returned empty choices")
                return "⚠️ Ошибка: API вернуло пустой ответ"
                
            # Extract and return response text
            return response.choices[0].message.content or "⚠️ Пустой ответ от API"
            
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return "⚠️ Превышен лимит запросов к OpenAI. Пожалуйста, попробуйте позже."
            
        except openai.AuthenticationError:
            logger.error("OpenAI authentication error")
            return "⚠️ API ключ OpenAI недействителен. Пожалуйста, проверьте ваш API ключ."
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return f"⚠️ Ошибка соединения с OpenAI: {str(e)}"
    
    async def generate_response_stream(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o"
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from OpenAI API.
        Returns an async generator that yields chunks of the response as they arrive.
        """
        try:
            # Проверка на пустой массив сообщений
            if not messages:
                logger.error("Empty messages array provided to OpenAI API")
                yield "⚠️ Ошибка: Пустой массив сообщений для API"
                return
                
            # Validate model
            if model not in config.available_models:
                model = config.default_model
                logger.warning(f"Invalid model requested. Using default: {model}")
            
            # Проверяем каждое сообщение на корректность
            for i, msg in enumerate(messages):
                if 'role' not in msg or 'content' not in msg:
                    logger.error(f"Invalid message format at index {i}: {msg}")
                    yield "⚠️ Ошибка: Некорректный формат сообщения"
                    return
                
                if not msg['content']:
                    logger.warning(f"Empty content in message at index {i}")
                    messages[i]['content'] = " "  # Заменяем пустую строку на пробел
            
            # Call OpenAI API with streaming
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True,  # Enable streaming
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Process the streaming response
            full_response = ""
            async for chunk in stream:
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                
                delta = chunk.choices[0].delta
                if not delta or not hasattr(delta, "content") or not delta.content:
                    continue
                
                full_response += delta.content
                yield full_response
            
            # If we didn't get any content, yield an error
            if not full_response:
                logger.error("OpenAI returned empty streaming response")
                yield "⚠️ Ошибка: API вернуло пустой ответ"
                
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            yield "⚠️ Превышен лимит запросов к OpenAI. Пожалуйста, попробуйте позже."
            
        except openai.AuthenticationError:
            logger.error("OpenAI authentication error")
            yield "⚠️ API ключ OpenAI недействителен. Пожалуйста, проверьте ваш API ключ."
            
        except Exception as e:
            logger.error(f"OpenAI API streaming error: {str(e)}")
            yield f"⚠️ Ошибка соединения с OpenAI: {str(e)}"
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key."""
        try:
            # Create a temporary client with the provided key
            client = AsyncOpenAI(api_key=api_key)
            
            # Make a simple request to validate the key
            await client.models.list()
            
            return True
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False 