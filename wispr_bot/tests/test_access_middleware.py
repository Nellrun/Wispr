import pytest
from unittest.mock import AsyncMock, patch

from ..middlewares.access import AccessMiddleware
from ..models.user import User


@pytest.mark.asyncio
async def test_middleware_allowed_user(mock_message, mock_user, mock_db):
    """Test middleware with allowed user."""
    # Setup allowed user
    mock_user.is_allowed = True
    
    # Mock DB to return our user
    mock_db.get_user.return_value = mock_user
    
    # Setup handler mock
    handler = AsyncMock()
    data = {}
    
    # Create middleware
    middleware = AccessMiddleware()
    
    # Call middleware
    await middleware(handler, mock_message, data)
    
    # Verify handler was called
    handler.assert_called_once_with(mock_message, {"user": mock_user})


@pytest.mark.asyncio
async def test_middleware_admin_user(mock_message, mock_user, mock_db):
    """Test middleware with admin user."""
    # Setup non-allowed user
    mock_user.is_allowed = False
    
    # Mock DB to return our user
    mock_db.get_user.return_value = mock_user
    
    # Setup handler mock
    handler = AsyncMock()
    data = {}
    
    # Create middleware
    middleware = AccessMiddleware()
    
    # Make sure user is in admin IDs
    with patch("wispr_bot.middlewares.access.config") as mock_config:
        mock_config.admin_user_ids = {123456789}  # Match our mock user ID
        
        # Call middleware
        await middleware(handler, mock_message, data)
        
        # Verify handler was called
        handler.assert_called_once_with(mock_message, {"user": mock_user})


@pytest.mark.asyncio
async def test_middleware_disallowed_user(mock_message, mock_user, mock_db):
    """Test middleware with disallowed user."""
    # Setup non-allowed user
    mock_user.is_allowed = False
    
    # Mock DB to return our user
    mock_db.get_user.return_value = mock_user
    
    # Setup handler mock
    handler = AsyncMock()
    data = {}
    
    # Create middleware
    middleware = AccessMiddleware()
    
    # Set admin IDs to not include our user
    with patch("wispr_bot.middlewares.access.config") as mock_config:
        mock_config.admin_user_ids = {999999}  # Different from our mock user ID
        
        # Call middleware
        await middleware(handler, mock_message, data)
        
        # Verify handler was NOT called
        handler.assert_not_called()
        
        # Verify message.answer was called with unauthorized message
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0]
        assert "not allowed" in args[0]


@pytest.mark.asyncio
async def test_middleware_new_user(mock_message, mock_db):
    """Test middleware with new user that doesn't exist in DB."""
    # Mock DB to return None (user doesn't exist)
    mock_db.get_user.return_value = None
    
    # Setup handler mock
    handler = AsyncMock()
    data = {}
    
    # Create middleware
    middleware = AccessMiddleware()
    
    # Set admin IDs to not include our user
    with patch("wispr_bot.middlewares.access.config") as mock_config:
        mock_config.admin_user_ids = {999999}  # Different from our mock user ID
        
        # Call middleware
        await middleware(handler, mock_message, data)
        
        # Verify handler was NOT called (user not allowed)
        handler.assert_not_called()
        
        # Verify create_or_update_user was called
        mock_db.create_or_update_user.assert_called_once()
        
        # Get the user that was created
        created_user = mock_db.create_or_update_user.call_args[0][0]
        assert created_user.telegram_id == mock_message.from_user.id
        assert created_user.username == mock_message.from_user.username
        assert created_user.is_allowed is False


@pytest.mark.asyncio
async def test_middleware_new_admin_user(mock_message, mock_db):
    """Test middleware with new admin user that doesn't exist in DB."""
    # Mock DB to return None (user doesn't exist)
    mock_db.get_user.return_value = None
    
    # Setup handler mock
    handler = AsyncMock()
    data = {}
    
    # Create middleware
    middleware = AccessMiddleware()
    
    # Set admin IDs to include our user
    with patch("wispr_bot.middlewares.access.config") as mock_config:
        mock_config.admin_user_ids = {123456789}  # Match our mock user ID
        
        # Call middleware
        await middleware(handler, mock_message, data)
        
        # Verify handler WAS called (user is admin)
        handler.assert_called_once()
        
        # Verify create_or_update_user was called
        mock_db.create_or_update_user.assert_called_once()
        
        # Get the user that was created
        created_user = mock_db.create_or_update_user.call_args[0][0]
        assert created_user.telegram_id == mock_message.from_user.id
        assert created_user.username == mock_message.from_user.username
        assert created_user.is_allowed is True  # Admin should be auto-allowed 