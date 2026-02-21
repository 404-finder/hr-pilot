"""
Termination command handler.

Handles /terminate command, parses the message, and triggers ADP automation.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config import settings
from src.telegram_bot.parsers import parse_termination

logger = logging.getLogger(__name__)


async def handle_termination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /terminate command.

    Parses the message and will trigger ADP termination automation (not yet implemented).

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.telegram_allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized termination attempt from user {update.effective_user.id}")
        return

    try:
        # Parse message
        logger.info("Parsing termination message")
        termination = parse_termination(update.message.text)
        logger.info(f"Parsed termination: {termination.first_name} {termination.last_name}")

        # Send processing message
        await update.message.reply_text(
            f"Processing termination for {termination.first_name} {termination.last_name}..."
        )

        # TODO: ADP termination automation not implemented yet
        # When implemented:
        # 1. Log into ADP
        # 2. Navigate to termination form
        # 3. Fill termination form
        # 4. Submit and confirm
        # 5. Send success message

        await update.message.reply_text("Termination workflow not yet implemented.")
        logger.info("Termination workflow not yet implemented")

    except ValueError as e:
        # Parsing error
        error_message = f"❌ Invalid message format:\n{str(e)}\n\nUse /help to see the expected format."
        await update.message.reply_text(error_message)
        logger.error(f"Parsing error: {e}")

    except Exception as e:
        # Unexpected error
        logger.error(f"Error processing termination: {e}", exc_info=True)
        error_message = f"❌ Error processing termination:\n{str(e)}"
        await update.message.reply_text(error_message)
