import asyncio
import os
from pathlib import Path

# Create logs directory if doesn't exist
Path("logs").mkdir(exist_ok=True)

# Import and run the bot
from .bot import start_bot

if __name__ == "__main__":
    asyncio.run(start_bot()) 