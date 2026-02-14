"""
New hire command handler.

Handles /newhire command, parses the message, and triggers ADP automation.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.adp.auth import login_to_adp
from src.adp.navigation import navigate_to_new_hire
from src.adp.new_hire_form import fill_new_hire_form
from src.adp.registration_code import send_registration_code
from src.config import settings
from src.telegram_bot.parsers import parse_new_hire, parse_new_hire_raw
from src.validators import validate_new_hire_input

logger = logging.getLogger(__name__)


async def handle_new_hire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newhire command.

    Parses the message, logs into ADP, fills the new hire form,
    and sends the registration code.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.telegram_allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized new hire attempt from user {update.effective_user.id}")
        return

    browser = None
    try:
        # Parse message into raw dict
        logger.info("Parsing new hire message")
        raw_data = parse_new_hire_raw(update.message.text)

        # Validate input against config_tables
        logger.info("Validating new hire input")
        validation_errors = validate_new_hire_input(raw_data)

        if validation_errors:
            # Send formatted error message
            error_message = "⚠️ Please fix the following:\n\n"
            error_message += "\n".join(f"• {error}" for error in validation_errors)
            await update.message.reply_text(error_message)
            logger.warning(f"Validation failed: {validation_errors}")
            return

        # Create validated Pydantic model
        hire = parse_new_hire(update.message.text)
        logger.info(f"Parsed new hire: {hire.first_name} {hire.last_name}")

        # Send processing message
        await update.message.reply_text(
            f"Processing new hire for {hire.first_name} {hire.last_name}..."
        )

        # Log into ADP
        logger.info("Logging into ADP")
        browser, page = await login_to_adp()

        # Navigate to new hire form
        logger.info("Navigating to new hire form")
        await navigate_to_new_hire(page)

        # Fill new hire form and capture Associate ID
        logger.info("Filling new hire form")
        associate_id = await fill_new_hire_form(page, hire)

        # Send registration code
        logger.info("Sending registration code")
        await send_registration_code(page, associate_id, hire.email)

        # Send success message
        success_message = (
            f"✅ New hire complete for {hire.first_name} {hire.last_name}.\n"
            f"Registration code sent to {hire.email}."
        )
        await update.message.reply_text(success_message)
        logger.info(f"Successfully processed new hire: {hire.first_name} {hire.last_name}")

    except ValueError as e:
        # Parsing error
        error_message = f"❌ Invalid message format:\n{str(e)}\n\nUse /help to see the expected format."
        await update.message.reply_text(error_message)
        logger.error(f"Parsing error: {e}")

    except Exception as e:
        # ADP automation error
        logger.error(f"Error processing new hire: {e}", exc_info=True)
        error_message = f"❌ Error processing new hire:\n{str(e)}"
        await update.message.reply_text(error_message)

        # Try to send screenshot if available
        try:
            if hasattr(e, 'screenshot_path') and e.screenshot_path:
                with open(e.screenshot_path, 'rb') as screenshot:
                    await update.message.reply_photo(
                        photo=screenshot,
                        caption="Error screenshot for debugging"
                    )
        except Exception as screenshot_error:
            logger.error(f"Failed to send screenshot: {screenshot_error}")

    finally:
        # Always close browser
        if browser:
            try:
                await browser.close()
                logger.info("Browser closed")
            except Exception as close_error:
                logger.error(f"Error closing browser: {close_error}")
