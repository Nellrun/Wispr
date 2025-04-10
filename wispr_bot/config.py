import os
from typing import List, Set
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config(BaseModel):
    """Application configuration settings."""
    
    # Bot settings
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_user_ids: Set[int] = {
        int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x
    }
    
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # OpenAI settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    available_models: List[str] = os.getenv("AVAILABLE_MODELS", "gpt-3.5-turbo").split(",")
    default_model: str = available_models[0] if available_models else "gpt-3.5-turbo"
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# Create config instance
config = Config() 