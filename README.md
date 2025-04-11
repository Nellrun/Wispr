# 🤖 Wispr Bot

Wispr Bot is a Telegram bot that serves as a proxy for OpenAI's ChatGPT models. It allows users to interact with various ChatGPT models directly through Telegram.

## ✨ Features

- 💬 Proxy requests to OpenAI's ChatGPT models
- 🔄 Support for multiple ChatGPT models (gpt-3.5-turbo, gpt-4, etc.)
- 👥 User whitelist system to control access
- 🔑 Personal API key support allowing users to use their own OpenAI API keys
- 📝 Multiple chat support with the ability to switch between conversations
- 🔒 Admin commands for managing users and permissions
- 🌊 Streaming response generation with dynamic updates
- 🔄 Request and response synchronization to prevent confusion
- 🖼️ Image generation using DALL-E 3

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wispr-bot.git
cd wispr-bot
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r wispr_bot/requirements.txt
```

3. Create a `.env` file in the `wispr_bot` directory (copy from `.env.example`):
```bash
cp wispr_bot/.env.example wispr_bot/.env
```

4. Edit the `.env` file with your configuration:
```
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_USER_IDS=your_telegram_id,another_admin_id

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/wispr_bot

# OpenAI Configuration
OPENAI_API_KEY=your_default_openai_api_key

# Allowed chat models
AVAILABLE_MODELS=gpt-3.5-turbo,gpt-4,gpt-4-turbo

# Log level
LOG_LEVEL=INFO
```

5. Initialize PostgreSQL database:
```bash
# Create database
createdb wispr_bot

# Run the schema creation script (using psql)
psql -d wispr_bot -f wispr_bot/database/schema.sql
```

## 🚀 Running the Bot

Run the bot using:

```bash
python -m wispr_bot
```

## 📝 Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/settings` - Configure your settings
- `/setapikey` - Set your OpenAI API key
- `/removeapikey` - Remove your API key
- `/setmodel` - Set your preferred model
- `/newchat` - Create a new chat
- `/chats` - Show all your chats
- `/currentchat` - Show current chat info
- `/clear_history` - Clear the history of the current chat
- `/exit` - Exit current chat
- `/image` - Generate images with DALL-E 3

### Admin Commands
- `/admin` - Show admin panel
- `/allow <user_id>` - Allow user to use bot
- `/disallow <user_id>` - Disallow user from using bot
- `/list_users` - List all allowed users
- `/stats` - Show bot statistics

## 📋 Implementation Features

### Image Generation with DALL-E 3
The bot supports image generation with DALL-E 3, allowing users to:
- Create images based on text prompts using the OpenAI API
- Generate images in different sizes and qualities
- Get both the image itself and the revised prompt used by DALL-E

### Streaming Response Generation
The bot uses streaming response generation from the OpenAI API (streaming mode), which allows:
- Displaying the response as it's being generated, so the user doesn't have to wait for the complete answer
- Handling long responses by breaking them into parts when necessary
- Improving bot responsiveness

### Request and Response Synchronization
The bot implements a mechanism for synchronizing requests and responses that:
- Prevents processing new messages until previous ones are completed
- Shows the user a notification if they try to send a message during processing
- Eliminates confusion between requests and responses

### Error Handling
The bot has enhanced error handling:
- Filtering error messages from the chat context
- Option to clear chat history when problems occur
- Clear and understandable error messages

## 🏗️ Deployment to Heroku

1. Make sure you have [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed.

2. Create a new Heroku application:
```bash
heroku create your-app-name
```

3. Add PostgreSQL add-on:
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

4. Set environment variables:
```bash
heroku config:set BOT_TOKEN=your_telegram_bot_token
heroku config:set ADMIN_USER_IDS=your_telegram_id,another_admin_id
heroku config:set OPENAI_API_KEY=your_default_openai_api_key
heroku config:set AVAILABLE_MODELS=gpt-3.5-turbo,gpt-4,gpt-4-turbo
```

5. Create a `Procfile` in the root directory:
```
web: python -m wispr_bot
```

6. Create a `runtime.txt` file in the root directory:
```
python-3.10.x
```

7. Deploy to Heroku:
```bash
git push heroku main
```

## 🧪 Testing

The bot includes a test suite to ensure functionality. Run tests with:

```bash
pytest wispr_bot/tests
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 