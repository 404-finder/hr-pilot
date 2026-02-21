"""
Entry point for the hr-pilot Telegram bot.

This module starts the Telegram bot and keeps it running to listen for
incoming commands (/newhire, /terminate, etc.).
"""

from src.telegram_bot.bot import create_bot
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__)


def main() -> None:
    """Main entry point for hr-pilot."""
    logger.info("hr-pilot starting...")
    logger.info("Initializing Telegram bot...")

    try:
        create_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
