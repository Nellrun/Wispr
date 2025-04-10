import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ..models.user import User
from ..models.chat import Chat, ChatMessage


@pytest.fixture
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_message():
    """Create mock Message object."""
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.chat = MagicMock()
    message.chat.id = 123456789
    message.text = "Hello, bot!"
    
    # Mock answer method
    message.answer = AsyncMock()
    
    return message


@pytest.fixture
def mock_callback_query():
    """Create mock CallbackQuery object."""
    callback = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.from_user.username = "test_user"
    callback.from_user.first_name = "Test"
    callback.from_user.last_name = "User"
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    callback.data = "test:data"
    
    # Mock answer method
    callback.answer = AsyncMock()
    
    return callback


@pytest.fixture
def mock_state():
    """Create mock FSMContext object."""
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    
    return state


@pytest.fixture
def mock_user():
    """Create mock User object."""
    return User(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        is_allowed=True
    )


@pytest.fixture
def mock_chat():
    """Create mock Chat object."""
    return Chat(
        id=1,
        user_id=123456789,
        title="Test Chat",
        model="gpt-3.5-turbo",
        messages=[
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!")
        ]
    )


@pytest.fixture
def mock_db():
    """Create mock Database object with AsyncMock methods."""
    with patch("wispr_bot.database.db.db") as mock:
        # Configure mock methods
        mock.get_user = AsyncMock()
        mock.create_or_update_user = AsyncMock()
        mock.get_chat = AsyncMock()
        mock.create_chat = AsyncMock()
        mock.get_user_chats = AsyncMock()
        mock.add_message = AsyncMock()
        mock.delete_chat = AsyncMock()
        mock.update_user_api_key = AsyncMock()
        mock.update_user_preferred_model = AsyncMock()
        mock.update_user_allowed_status = AsyncMock()
        mock.get_allowed_users = AsyncMock()
        
        yield mock


@pytest.fixture
def mock_openai_service():
    """Create mock OpenAIService object with AsyncMock methods."""
    with patch("wispr_bot.services.openai_service.OpenAIService") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.generate_response = AsyncMock(return_value="This is a test response from the mock OpenAI service.")
        mock_instance.validate_api_key = AsyncMock(return_value=True)
        
        mock_class.return_value = mock_instance
        yield mock_class 