import asyncpg
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..utils.logger import logger
from ..config import config
from ..models.user import User
from ..models.chat import Chat, ChatMessage


class Database:
    """Database manager for PostgreSQL operations."""
    
    def __init__(self):
        self.pool = None
    
    async def connect(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            self.pool = await asyncpg.create_pool(config.database_url)
            logger.info("Connected to database")
            await self._initialize_database()
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL database."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from database")
    
    async def _initialize_database(self) -> None:
        """Initialize database schema if not exists."""
        try:
            schema_path = Path(__file__).parent / "schema.sql"
            schema = schema_path.read_text()
            
            async with self.pool.acquire() as conn:
                await conn.execute(schema)
                logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise

    # User operations
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM users WHERE telegram_id = $1
                """, 
                telegram_id
            )
            
            if not row:
                return None
                
            return User(**dict(row))
    
    async def create_or_update_user(self, user: User) -> User:
        """Create or update user."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users 
                (telegram_id, username, first_name, last_name, is_allowed, openai_api_key, preferred_model, created_at, last_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET
                    username = $2,
                    first_name = $3,
                    last_name = $4,
                    is_allowed = $5,
                    openai_api_key = $6,
                    preferred_model = $7,
                    last_active = $9
                """,
                user.telegram_id, user.username, user.first_name, user.last_name,
                user.is_allowed, user.openai_api_key, user.preferred_model,
                user.created_at, user.last_active
            )
            
            return user
    
    async def update_user_allowed_status(self, telegram_id: int, is_allowed: bool) -> None:
        """Update user's allowed status."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET is_allowed = $1 WHERE telegram_id = $2
                """,
                is_allowed, telegram_id
            )
    
    async def update_user_api_key(self, telegram_id: int, api_key: Optional[str]) -> None:
        """Update user's OpenAI API key."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET openai_api_key = $1 WHERE telegram_id = $2
                """,
                api_key, telegram_id
            )
    
    async def update_user_preferred_model(self, telegram_id: int, model: str) -> None:
        """Update user's preferred ChatGPT model."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET preferred_model = $1 WHERE telegram_id = $2
                """,
                model, telegram_id
            )
    
    async def get_allowed_users(self) -> List[User]:
        """Get all allowed users."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE is_allowed = TRUE")
            return [User(**dict(row)) for row in rows]
    
    # Chat operations
    async def create_chat(self, user_id: int, title: str, model: str, system_prompt: Optional[str] = None) -> Chat:
        """Create a new chat."""
        async with self.pool.acquire() as conn:
            chat_id = await conn.fetchval(
                """
                INSERT INTO chats (user_id, title, model, system_prompt)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                user_id, title, model, system_prompt
            )
            
            return Chat(
                id=chat_id,
                user_id=user_id,
                title=title,
                model=model,
                system_prompt=system_prompt,
                messages=[]
            )
    
    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        """Get chat by ID with messages."""
        async with self.pool.acquire() as conn:
            # Get chat details
            chat_row = await conn.fetchrow("SELECT * FROM chats WHERE id = $1", chat_id)
            if not chat_row:
                return None
                
            chat_dict = dict(chat_row)
            
            # Get chat messages
            message_rows = await conn.fetch(
                """
                SELECT role, content, timestamp FROM messages 
                WHERE chat_id = $1 
                ORDER BY timestamp ASC
                """, 
                chat_id
            )
            
            messages = [ChatMessage(**dict(row)) for row in message_rows]
            
            return Chat(
                id=chat_dict["id"],
                user_id=chat_dict["user_id"],
                title=chat_dict["title"],
                model=chat_dict["model"],
                messages=messages,
                created_at=chat_dict["created_at"],
                updated_at=chat_dict["updated_at"],
                system_prompt=chat_dict["system_prompt"]
            )
    
    async def get_user_chats(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all chats for a user (without messages for performance)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, model, created_at, updated_at 
                FROM chats 
                WHERE user_id = $1
                ORDER BY updated_at DESC
                """, 
                user_id
            )
            
            return [dict(row) for row in rows]
    
    async def add_message(self, chat_id: int, role: str, content: str) -> None:
        """Add a message to a chat."""
        async with self.pool.acquire() as conn:
            # Add message
            await conn.execute(
                """
                INSERT INTO messages (chat_id, role, content)
                VALUES ($1, $2, $3)
                """,
                chat_id, role, content
            )
            
            # Update chat's updated_at timestamp
            await conn.execute(
                """
                UPDATE chats SET updated_at = $1 WHERE id = $2
                """,
                datetime.now(), chat_id
            )
    
    async def delete_chat(self, chat_id: int) -> bool:
        """Delete a chat."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM chats WHERE id = $1
                """,
                chat_id
            )
            return "DELETE" in result


# Create database instance
db = Database() 