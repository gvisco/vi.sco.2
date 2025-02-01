#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
Vito Scognamiglio, my personal assistant.

Vito takes input and interacts via Telegram.
"""

import logging
import json
import sys
import os
from pathlib import Path
from typing import Dict, List

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def load_json_file(filename: str):
    """Load a JSON file or exit if not found."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{filename} not found. Please create the file with required configuration.")
        sys.exit(1)

# Load configuration files
ALLOWED_USERS = load_json_file("allowed_users.json")
CONFIG = load_json_file("private.json")

def load_chat_memory(user_id: int, username: str) -> dict:
    """Load or create chat memory for a user."""
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    memory_file = f"data/{user_id}.json"
    try:
        with open(memory_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize new memory file
        memory = {
            "username": username,
            "messages": []
        }
        save_chat_memory(user_id, memory)
        return memory

def save_chat_memory(user_id: int, memory: dict):
    """Save chat memory to file."""
    with open(f"data/{user_id}.json", "w") as f:
        json.dump(memory, f, indent=2)

def update_message_history(messages: list, new_message: dict):
    """Update message history keeping last 20 messages."""
    messages.append(new_message)
    return messages[-20:] if len(messages) > 20 else messages

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a new message from the user."""
    # check if the user is allowed to send messages
    user_id = update.effective_user.id
    
    if user_id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized message attempt from user ID: {user_id}")
        return
    
    logger.debug(f"Received message from user ID: {user_id}")
    
    # Load chat memory
    memory = load_chat_memory(user_id, update.effective_user.username or str(user_id))
    
    # Add user message to history
    memory["messages"] = update_message_history(
        memory["messages"],
        {"from": "user", "text": update.message.text}
    )
    
    # TODO: generate reply
    reply = update.message.text

    # Send reply
    await update.message.reply_text(reply)
    
    # Add bot response to history and save
    memory["messages"] = update_message_history(
        memory["messages"],
        {"from": "bot", "text": reply}
    )
    save_chat_memory(user_id, memory)

async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete user's chat history."""
    user_id = update.effective_user.id
    
    if user_id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized clear attempt from user ID: {user_id}")
        return
    
    data_file = Path(f"data/{user_id}.json")
    if data_file.exists():
        data_file.unlink()
        logger.info(f"Deleted chat history for user ID: {user_id}")
        await update.message.reply_text("Your chat history has been cleared.")
    else:
        await update.message.reply_text("No chat history found.")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(CONFIG['telegram_token']).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("clear", clear_data))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()