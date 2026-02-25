"""
New hire command handler.

Handles /newhire command with dry-run preview and /confirm to submit.
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
    """Handle /newhire command with dry-run preview.

    Parses the message, logs into ADP, fills the form in dry-run mode,
    and waits for user confirmation before submitting.

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
            error_message = "[WARNING] Please fix the following:\n\n"
            error_message += "\n".join(f"  {error}" for error in validation_errors)
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

        # Fill new hire form in DRY RUN mode
        logger.info("Filling new hire form (dry run mode)")
        result = await fill_new_hire_form(page, hire, dry_run=True)

        # Send screenshot to user for review
        with open(result["screenshot_path"], 'rb') as screenshot:
            await update.message.reply_photo(
                photo=screenshot,
                caption=f"[OK] Form filled for {hire.first_name} {hire.last_name}"
            )

        # Surface any warnings (e.g. manager not found)
        if result.get("warnings"):
            warning_text = "[WARNING] The following issues occurred:\n" + "\n".join(
                f"  - {w}" for w in result["warnings"]
            )
            await update.message.reply_text(warning_text)

        # Send confirmation prompt
        confirmation_message = (
            f"Review the screenshot above.\n\n"
            f"Reply /confirm to submit or /cancel to discard."
        )
        await update.message.reply_text(confirmation_message)

        # Store data in context for /confirm to use
        context.user_data["pending_hire"] = True
        context.user_data["browser"] = browser
        context.user_data["page"] = page
        context.user_data["hire"] = hire
        context.user_data["associate_id"] = result["associate_id"]

        # Schedule auto-cancel after 5 minutes
        if context.job_queue:
            context.job_queue.run_once(
                auto_cancel_hire,
                300,  # 5 minutes
                chat_id=update.effective_chat.id,
                user_id=update.effective_user.id,
                data={"user_id": update.effective_user.id}
            )

        logger.info(f"Waiting for confirmation for: {hire.first_name} {hire.last_name}")

    except ValueError as e:
        # Parsing error
        error_message = f"[FAIL] Invalid message format:\n{str(e)}\n\nUse /help to see the expected format."
        await update.message.reply_text(error_message)
        logger.error(f"Parsing error: {e}")

        # Close browser if opened
        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    except Exception as e:
        # ADP automation error
        logger.error(f"Error processing new hire: {e}", exc_info=True)
        error_message = f"[FAIL] Error processing new hire:\n{str(e)}"
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

        # Close browser if opened
        if browser:
            try:
                await browser.close()
            except Exception:
                pass


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /confirm command to submit the pending new hire form.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.telegram_allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        return

    # Check if there's a pending hire
    if not context.user_data.get("pending_hire"):
        await update.message.reply_text("No pending hire to confirm.")
        return

    browser = None
    page = None

    try:
        # Get stored data
        browser = context.user_data.get("browser")
        page = context.user_data.get("page")
        hire = context.user_data.get("hire")
        associate_id = context.user_data.get("associate_id")

        if not page or not hire or not associate_id:
            await update.message.reply_text("[FAIL] Session data missing. Please start over with /newhire.")
            return

        logger.info(f"Confirming submission for: {hire.first_name} {hire.last_name}")
        await update.message.reply_text(f"Submitting form for {hire.first_name} {hire.last_name}...")

        # Import the Save and Exit button selector
        from src.adp.selectors.new_hire import SAVE_AND_EXIT_BUTTON

        # Click Save and Exit
        await page.wait_for_selector(SAVE_AND_EXIT_BUTTON, timeout=10000)
        await page.click(SAVE_AND_EXIT_BUTTON)

        # Wait for save confirmation
        await page.wait_for_timeout(3000)

        # Take success screenshot
        from src.utils.screenshots import capture_screenshot
        screenshot_filename = f"new_hire_submitted_{hire.first_name}_{hire.last_name}".replace(" ", "_")
        screenshot_path = await capture_screenshot(page, screenshot_filename)

        # Send success screenshot
        with open(screenshot_path, 'rb') as screenshot:
            await update.message.reply_photo(
                photo=screenshot,
                caption=f"[OK] Form submitted for {hire.first_name} {hire.last_name}"
            )

        # Send registration code
        logger.info(f"Sending registration code for Associate ID: {associate_id}")
        await send_registration_code(page, associate_id, hire.email)

        # Send final success message
        success_message = (
            f"[OK] New hire complete for {hire.first_name} {hire.last_name}.\n"
            f"Registration code sent to {hire.email}."
        )
        await update.message.reply_text(success_message)
        logger.info(f"Successfully completed new hire: {hire.first_name} {hire.last_name}")

    except Exception as e:
        logger.error(f"Error confirming new hire: {e}", exc_info=True)
        error_message = f"[FAIL] Error submitting form:\n{str(e)}"
        await update.message.reply_text(error_message)

    finally:
        # Always close browser and clear data
        if browser:
            try:
                await browser.close()
                logger.info("Browser closed after confirmation")
            except Exception as close_error:
                logger.error(f"Error closing browser: {close_error}")

        # Clear pending hire data
        context.user_data.pop("pending_hire", None)
        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)
        context.user_data.pop("associate_id", None)


async def handle_cancel_hire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command to discard the pending new hire.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.telegram_allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        return

    # Check if there's a pending hire
    if not context.user_data.get("pending_hire"):
        await update.message.reply_text("No pending hire to cancel.")
        return

    try:
        # Get stored browser
        browser = context.user_data.get("browser")

        # Close browser
        if browser:
            await browser.close()
            logger.info("Browser closed after cancellation")

        # Clear pending hire data
        context.user_data.pop("pending_hire", None)
        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)
        context.user_data.pop("associate_id", None)

        await update.message.reply_text("[FAIL] New hire cancelled.")
        logger.info("Pending hire cancelled by user")

    except Exception as e:
        logger.error(f"Error cancelling hire: {e}", exc_info=True)
        await update.message.reply_text(f"Error during cancellation: {str(e)}")


async def auto_cancel_hire(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-cancel pending hire after timeout.

    This is called by job_queue after 5 minutes if no confirmation received.

    Args:
        context: Telegram context object.
    """
    job = context.job
    user_id = job.data.get("user_id")

    # Check if there's still a pending hire
    if not context.user_data.get("pending_hire"):
        return  # Already confirmed or cancelled

    try:
        # Get stored browser
        browser = context.user_data.get("browser")

        # Close browser
        if browser:
            await browser.close()
            logger.info("Browser closed after auto-cancel timeout")

        # Clear pending hire data
        context.user_data.pop("pending_hire", None)
        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)
        context.user_data.pop("associate_id", None)

        # Send timeout message
        await context.bot.send_message(
            chat_id=job.chat_id,
            text="[WARNING] New hire request timed out after 5 minutes. Please start over with /newhire."
        )
        logger.info(f"Auto-cancelled pending hire for user {user_id} due to timeout")

    except Exception as e:
        logger.error(f"Error during auto-cancel: {e}", exc_info=True)
