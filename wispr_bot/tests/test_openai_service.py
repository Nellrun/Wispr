import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ..services.openai_service import OpenAIService
from ..config import config


@pytest.mark.asyncio
async def test_openai_service_init():
    """Test OpenAIService initialization."""
    # Test with default API key
    with patch("openai.AsyncOpenAI") as mock_openai:
        service = OpenAIService()
        mock_openai.assert_called_once_with(api_key=config.openai_api_key)
        assert service.api_key == config.openai_api_key
    
    # Test with custom API key
    custom_key = "sk-custom-key"
    with patch("openai.AsyncOpenAI") as mock_openai:
        service = OpenAIService(api_key=custom_key)
        mock_openai.assert_called_once_with(api_key=custom_key)
        assert service.api_key == custom_key


@pytest.mark.asyncio
async def test_update_api_key():
    """Test updating API key."""
    with patch("openai.AsyncOpenAI") as mock_openai:
        service = OpenAIService()
        mock_openai.reset_mock()
        
        # Update API key
        new_key = "sk-new-key"
        service.update_api_key(new_key)
        
        # Check if client was reinitialized
        mock_openai.assert_called_once_with(api_key=new_key)
        assert service.api_key == new_key


@pytest.mark.asyncio
async def test_generate_response_success():
    """Test successful generation of responses."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    
    # Mock response from OpenAI
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Hello! How can I help you today?"
    
    # Create mock client
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        service = OpenAIService()
        response = await service.generate_response(messages, model="gpt-3.5-turbo")
        
        # Verify response
        assert response == "Hello! How can I help you today?"
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        assert call_args["messages"] == messages


@pytest.mark.asyncio
async def test_generate_response_invalid_model():
    """Test response generation with an invalid model."""
    messages = [{"role": "user", "content": "Hello!"}]
    
    # Mock response
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Hello there!"
    
    # Create mock client
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        # Set available models in config
        with patch.object(config, "available_models", ["gpt-3.5-turbo"]):
            with patch.object(config, "default_model", "gpt-3.5-turbo"):
                service = OpenAIService()
                
                # Try with invalid model
                response = await service.generate_response(messages, model="invalid-model")
                
                # Verify default model was used
                call_args = mock_client.chat.completions.create.call_args[1]
                assert call_args["model"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_generate_response_errors():
    """Test error handling in generate_response."""
    messages = [{"role": "user", "content": "Hello!"}]
    
    # Test rate limit error
    with patch("openai.AsyncOpenAI") as mock_openai_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        mock_openai_class.return_value = mock_client
        
        service = OpenAIService()
        response = await service.generate_response(messages)
        
        # Verify error message
        assert "Error connecting to OpenAI" in response


@pytest.mark.asyncio
async def test_validate_api_key_valid():
    """Test validation of valid API key."""
    # Mock successful models.list call
    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock()
    
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        service = OpenAIService()
        valid = await service.validate_api_key("sk-valid-key")
        
        # Verify validation result
        assert valid is True
        mock_client.models.list.assert_called_once()


@pytest.mark.asyncio
async def test_validate_api_key_invalid():
    """Test validation of invalid API key."""
    # Mock failed models.list call
    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(side_effect=Exception("Invalid API key"))
    
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        service = OpenAIService()
        valid = await service.validate_api_key("sk-invalid-key")
        
        # Verify validation result
        assert valid is False
        mock_client.models.list.assert_called_once() 