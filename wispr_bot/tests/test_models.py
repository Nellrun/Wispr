import pytest
from datetime import datetime

from ..models.user import User
from ..models.chat import Chat, ChatMessage


def test_user_model():
    """Test User model functionality."""
    # Test creation and default values
    user = User(telegram_id=123456789)
    assert user.telegram_id == 123456789
    assert user.username is None
    assert user.first_name is None
    assert user.last_name is None
    assert user.is_allowed is False
    assert user.openai_api_key is None
    assert user.preferred_model is None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.last_active, datetime)
    
    # Test with all values provided
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        is_allowed=True,
        openai_api_key="sk-test123",
        preferred_model="gpt-4",
        created_at=datetime(2023, 1, 1),
        last_active=datetime(2023, 1, 2)
    )
    
    assert user.telegram_id == 123456789
    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.is_allowed is True
    assert user.openai_api_key == "sk-test123"
    assert user.preferred_model == "gpt-4"
    assert user.created_at == datetime(2023, 1, 1)
    assert user.last_active == datetime(2023, 1, 2)
    
    # Test properties
    assert user.full_name == "Test User"
    assert user.has_custom_api_key is True
    
    # Test properties with partial data
    user = User(telegram_id=123456789, first_name="Test")
    assert user.full_name == "Test"
    assert user.has_custom_api_key is False
    
    user = User(telegram_id=123456789, username="testuser")
    assert user.full_name == "testuser"
    
    # Test with empty string API key
    user = User(telegram_id=123456789, openai_api_key="")
    assert user.has_custom_api_key is False


def test_chat_message_model():
    """Test ChatMessage model functionality."""
    # Test creation and default values
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert isinstance(msg.timestamp, datetime)
    
    # Test with all values provided
    timestamp = datetime(2023, 1, 1, 12, 0, 0)
    msg = ChatMessage(
        role="assistant",
        content="Hi there!",
        timestamp=timestamp
    )
    
    assert msg.role == "assistant"
    assert msg.content == "Hi there!"
    assert msg.timestamp == timestamp


def test_chat_model():
    """Test Chat model functionality."""
    # Test creation and default values
    chat = Chat(id=1, user_id=123456789, title="Test Chat", model="gpt-3.5-turbo")
    assert chat.id == 1
    assert chat.user_id == 123456789
    assert chat.title == "Test Chat"
    assert chat.model == "gpt-3.5-turbo"
    assert chat.messages == []
    assert isinstance(chat.created_at, datetime)
    assert isinstance(chat.updated_at, datetime)
    assert chat.system_prompt is None
    
    # Test with all values and messages
    created_at = datetime(2023, 1, 1)
    updated_at = datetime(2023, 1, 2)
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!")
    ]
    
    chat = Chat(
        id=1,
        user_id=123456789,
        title="Test Chat",
        model="gpt-4",
        messages=messages,
        created_at=created_at,
        updated_at=updated_at,
        system_prompt="You are a helpful assistant."
    )
    
    assert chat.id == 1
    assert chat.user_id == 123456789
    assert chat.title == "Test Chat"
    assert chat.model == "gpt-4"
    assert len(chat.messages) == 2
    assert chat.messages[0].role == "user"
    assert chat.messages[0].content == "Hello"
    assert chat.messages[1].role == "assistant"
    assert chat.messages[1].content == "Hi there!"
    assert chat.created_at == created_at
    assert chat.updated_at == updated_at
    assert chat.system_prompt == "You are a helpful assistant."
    
    # Test add_message method
    original_timestamp = chat.updated_at
    chat.add_message("user", "How are you?")
    
    assert len(chat.messages) == 3
    assert chat.messages[2].role == "user"
    assert chat.messages[2].content == "How are you?"
    assert chat.updated_at > original_timestamp
    
    # Test get_context_messages method
    context = chat.get_context_messages()
    
    assert len(context) == 4  # system + 3 messages
    assert context[0]["role"] == "system"
    assert context[0]["content"] == "You are a helpful assistant."
    assert context[1]["role"] == "user"
    assert context[1]["content"] == "Hello"
    assert context[2]["role"] == "assistant"
    assert context[2]["content"] == "Hi there!"
    assert context[3]["role"] == "user"
    assert context[3]["content"] == "How are you?" 