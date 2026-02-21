"""
Bot setup and handler registration.

Creates the Telegram bot application and registers all command handlers.
"""

from telegram.ext import ApplicationBuilder, CommandHandler

from src.config import settings
from src.telegram_bot.handlers.common import cancel, error_handler, help_command, start
from src.telegram_bot.handlers.new_hire import handle_new_hire, handle_confirm, handle_cancel_hire
from src.telegram_bot.handlers.termination import handle_termination
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_bot() -> None:
    """Build and start the Telegram bot.

    Registers all command handlers and starts polling for updates.
    """
    logger.info("Building Telegram bot application")

    # Build application
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("newhire", handle_new_hire))
    app.add_handler(CommandHandler("confirm", handle_confirm))
    app.add_handler(CommandHandler("cancel", handle_cancel_hire))
    app.add_handler(CommandHandler("terminate", handle_termination))

    # Register error handler
    app.add_error_handler(error_handler)

    logger.info("Bot handlers registered")
    logger.info("Starting bot polling...")

    # Start polling
    app.run_polling()
