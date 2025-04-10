from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Model representing a single message in a chat."""
    
    role: str  # 'user', 'assistant', or 'system'
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Chat(BaseModel):
    """Model representing a conversation thread."""
    
    id: int
    user_id: int
    title: str
    model: str
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    system_prompt: Optional[str] = None
    
    def add_message(self, role: str, content: str) -> None:
        """Add a new message to the chat."""
        self.messages.append(
            ChatMessage(role=role, content=content)
        )
        self.updated_at = datetime.now()
    
    def get_context_messages(self, current_user_message: Optional[str] = None, max_tokens: int = 4000) -> List[dict]:
        """
        Get messages formatted for OpenAI API with token limit.
        This is a simplified version - in a real app, you'd need to count tokens properly.
        """
        formatted_messages = []
        
        # Add system prompt if it exists
        if self.system_prompt:
            formatted_messages.append({"role": "system", "content": self.system_prompt})
        
        # Add conversation history, newest last
        user_messages = []
        for msg in self.messages[-20:]:  # Simplified token management - just keep last 20 messages
            # Проверяем, не содержит ли сообщение ошибку
            if msg.role == 'assistant' and msg.content.startswith('⚠️ Ошибка'):
                continue  # Пропускаем сообщения с ошибками
            
            user_messages.append({"role": msg.role, "content": msg.content})
        
        # Если в результате фильтрации у нас не осталось сообщений, добавим базовое приветствие
        if not user_messages and not formatted_messages:
            # Если ничего нет, хотя бы добавим системное сообщение для инициализации диалога
            formatted_messages.append({
                "role": "system", 
                "content": "Вы полезный ассистент, который отвечает на вопросы пользователя."
            })
        else:
            formatted_messages.extend(user_messages)
        
        if current_user_message:
            formatted_messages.append({"role": "user", "content": current_user_message})
            
        return formatted_messages 