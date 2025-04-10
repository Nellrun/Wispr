from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    """User model representing a Telegram user."""
    
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_allowed: bool = False
    openai_api_key: Optional[str] = None
    preferred_model: Optional[str] = None
    created_at: datetime = datetime.now()
    last_active: datetime = datetime.now()
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)
    
    @property
    def has_custom_api_key(self) -> bool:
        """Check if user has a custom API key."""
        return self.openai_api_key is not None and len(self.openai_api_key) > 0 