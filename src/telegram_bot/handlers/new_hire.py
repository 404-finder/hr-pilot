"""
New hire command handler.

Handles /newhire command with dry-run preview and /confirm to submit.
"""

import glob
import os

from telegram import Update
from telegram.ext import ContextTypes

from src.adp.auth import login_to_adp
from src.adp.navigation import navigate_to_new_hire
from src.adp.new_hire_form import fill_new_hire_form
from src.adp.registration_code import send_registration_code
from src.adp.selectors.new_hire import SAVE_AND_EXIT_BUTTON
from src.config import settings
from src.telegram_bot.parsers import parse_new_hire, parse_new_hire_raw
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot
from src.validators import validate_new_hire_input

logger = setup_logger(__name__)


async def _run_new_hire_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    browser,
    page,
    hire,
) -> None:
    """Navigate ADP and fill the new hire form in dry-run mode, then prompt for confirmation.

    Shared by both the non-MFA path (called directly from handle_new_hire)
    and the MFA path (called from handle_mfa_code after code verification).

    Args:
        update: Telegram update object.
        context: Telegram context object.
        browser: Authenticated Playwright browser.
        page: Authenticated ADP page.
        hire: Validated NewHire model instance.
    """
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
    await update.message.reply_text(
        "Review the screenshot above.\n\n"
        "Reply /confirm to submit or /cancel to discard."
    )

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


async def handle_new_hire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newhire command with dry-run preview.

    Parses the message, logs into ADP, fills the form in dry-run mode,
    and waits for user confirmation before submitting.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
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

        # Get ADP credentials for this Telegram user
        try:
            adp_creds = settings.get_adp_credentials(update.effective_user.id)
        except ValueError as creds_error:
            await update.message.reply_text(f"[FAIL] {creds_error}")
            logger.error(f"Credentials lookup failed: {creds_error}")
            return

        # Log into ADP
        logger.info("Logging into ADP")
        browser, page, mfa_required = await login_to_adp(
            username=adp_creds.username,
            password=adp_creds.password.get_secret_value(),
        )

        if mfa_required:
            # Store state and wait for user to supply the MFA code
            context.user_data["awaiting_mfa_code"] = True
            context.user_data["browser"] = browser
            context.user_data["page"] = page
            context.user_data["hire"] = hire

            if context.job_queue:
                context.job_queue.run_once(
                    auto_cancel_mfa,
                    180,  # 3 minutes
                    chat_id=update.effective_chat.id,
                    user_id=update.effective_user.id,
                    data={"user_id": update.effective_user.id}
                )

            await update.message.reply_text(
                "ADP requires identity verification.\n"
                "A text message has been sent to your phone.\n\n"
                "Please reply with the verification code."
            )
            logger.info("MFA required — waiting for user to supply code")
            return

        # No MFA — proceed directly
        await _run_new_hire_flow(update, context, browser, page, hire)

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

        # Send the most recent screenshot for debugging
        try:
            files = glob.glob(os.path.join(settings.screenshot_dir, "*.png"))
            if files:
                latest = max(files, key=os.path.getmtime)
                with open(latest, "rb") as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=f"Debug: {os.path.basename(latest)}",
                    )
        except Exception as screenshot_error:
            logger.error(f"Failed to send debug screenshot: {screenshot_error}")

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
    if update.effective_user.id not in settings.allowed_user_ids:
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

        # --- Step 1: Save and Exit ---
        try:
            await page.wait_for_selector(SAVE_AND_EXIT_BUTTON, timeout=10000)
            await page.click(SAVE_AND_EXIT_BUTTON)
            await page.wait_for_timeout(3000)

            screenshot_filename = f"new_hire_submitted_{hire.first_name}_{hire.last_name}".replace(" ", "_")
            screenshot_path = await capture_screenshot(page, screenshot_filename)

            with open(screenshot_path, 'rb') as screenshot:
                await update.message.reply_photo(
                    photo=screenshot,
                    caption=f"[OK] Form submitted for {hire.first_name} {hire.last_name}"
                )

            logger.info(f"Form submitted for {hire.first_name} {hire.last_name}")

        except Exception as e:
            logger.error(f"Error submitting form: {e}", exc_info=True)
            await update.message.reply_text(f"[FAIL] Error submitting form:\n{str(e)}")
            return

        # --- Step 2: Registration Code ---
        try:
            logger.info(f"Sending registration code for Associate ID: {associate_id}")
            await send_registration_code(page, associate_id, hire.email)

            await update.message.reply_text(
                f"[OK] Registration code sent to {hire.email}."
            )
            logger.info(f"Registration code sent for {hire.first_name} {hire.last_name}")

        except Exception as e:
            logger.warning(f"Registration code failed: {e}", exc_info=True)
            await update.message.reply_text(
                f"Form was saved successfully but registration code failed.\n"
                f"Associate ID: {associate_id}\n"
                f"You can send the registration code manually from ADP Security Management."
            )

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
    if update.effective_user.id not in settings.allowed_user_ids:
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


async def handle_mfa_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the MFA verification code sent by the user as a plain text message.

    Only acts when context.user_data["awaiting_mfa_code"] is set (i.e. ADP
    presented an MFA challenge during the current /newhire flow). All other
    plain-text messages are silently ignored.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Ignore if we are not waiting for an MFA code
    if not context.user_data.get("awaiting_mfa_code"):
        return

    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        return

    code = update.message.text.strip()
    browser = context.user_data.get("browser")
    page = context.user_data.get("page")
    hire = context.user_data.get("hire")

    # Clear the flag immediately to prevent re-entry on duplicate messages
    context.user_data.pop("awaiting_mfa_code", None)

    try:
        logger.info("Received MFA code — submitting to ADP")

        # Fill in the verification code using the Passcode label.
        code_input = page.get_by_label("Passcode")
        await code_input.click()
        await code_input.fill(code)

        # Debug: screenshot + page source before attempting submit
        await page.screenshot(path="screenshots/mfa_pre_submit_debug.png")
        logger.info("MFA pre-submit screenshot saved")
        content = await page.content()
        with open("screenshots/mfa_page_source.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("MFA page source saved to screenshots/mfa_page_source.html")

        # Try progressively broader selectors for the submit element
        submitted = False
        for locator in [
            page.get_by_role("button", name="Submit"),
            page.locator("[type='submit']"),
            page.locator("text=Submit"),
        ]:
            try:
                await locator.click(timeout=5000)
                submitted = True
                logger.info(f"Submit clicked via locator: {locator}")
                break
            except Exception:
                continue
        if not submitted:
            raise Exception("Could not find Submit button — check screenshots/mfa_pre_submit_debug.png")

        # Wait for dashboard redirect after successful verification
        logger.info("Waiting for dashboard after MFA verification")
        await page.wait_for_url("https://workforcenow.adp.com/**", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        logger.info(f"Post-MFA URL: {page.url}")

        # Dismiss "Remind me later" popup if it appears
        try:
            await page.wait_for_selector(
                'sdf-button[aria-label="Remind me later"]', timeout=5000
            )
            await page.click('sdf-button[aria-label="Remind me later"]')
            logger.info("Dismissed post-MFA popup")
        except Exception:
            pass

        # Dismiss Pendo overlay if it appeared after MFA
        from src.adp.base_form import dismiss_pendo
        await dismiss_pendo(page)

        # Determine which flow triggered MFA
        check_status_params = context.user_data.get("check_status_params")

        if check_status_params:
            await update.message.reply_text(
                "Identity verified. Continuing with status check..."
            )
            logger.info("MFA verified — proceeding with check status flow")
        else:
            await update.message.reply_text(
                "Identity verified. Continuing with new hire form..."
            )
            logger.info("MFA verified — proceeding with new hire flow")

    except Exception as e:
        logger.error(f"MFA verification failed: {e}", exc_info=True)

        try:
            await capture_screenshot(page, "mfa_verification_error")
        except Exception:
            pass

        await update.message.reply_text(
            f"[FAIL] MFA verification failed:\n{str(e)}\n\n"
            "Please try again."
        )

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)
        context.user_data.pop("check_status_params", None)
        return

    # MFA succeeded — continue with the appropriate flow (separate try/except
    # so errors here are reported accurately, not as "MFA verification failed")
    check_status_params = context.user_data.get("check_status_params")

    if check_status_params:
        # Check status flow
        try:
            from src.telegram_bot.handlers.check_status import _run_check_status
            context.user_data.pop("check_status_params", None)
            await _run_check_status(update, context, browser, page, check_status_params)
        except Exception as e:
            logger.error(f"Error checking status after MFA: {e}", exc_info=True)
            await update.message.reply_text(f"[FAIL] Error checking status:\n{str(e)}")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            context.user_data.pop("browser", None)
            context.user_data.pop("page", None)
        return

    # New hire flow
    try:
        await _run_new_hire_flow(update, context, browser, page, hire)

    except Exception as e:
        logger.error(f"Error processing new hire after MFA: {e}", exc_info=True)

        await update.message.reply_text(
            f"[FAIL] Error processing new hire:\n{str(e)}"
        )

        # Send the most recent screenshot for debugging
        try:
            files = glob.glob(os.path.join(settings.screenshot_dir, "*.png"))
            if files:
                latest = max(files, key=os.path.getmtime)
                with open(latest, "rb") as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=f"Debug: {os.path.basename(latest)}",
                    )
        except Exception:
            pass

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)


async def auto_cancel_mfa(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-cancel MFA verification after 3 minutes if no code is received.

    Called by job_queue 3 minutes after ADP triggers MFA.

    Args:
        context: Telegram context object.
    """
    job = context.job
    user_id = job.data.get("user_id")

    # Already completed or cancelled
    if not context.user_data.get("awaiting_mfa_code"):
        return

    try:
        browser = context.user_data.get("browser")
        if browser:
            await browser.close()
            logger.info("Browser closed after MFA timeout")

        context.user_data.pop("awaiting_mfa_code", None)
        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("hire", None)
        context.user_data.pop("check_status_params", None)

        await context.bot.send_message(
            chat_id=job.chat_id,
            text=(
                "[WARNING] MFA verification timed out after 3 minutes. "
                "Please try again with /newhire."
            )
        )
        logger.info(f"Auto-cancelled MFA for user {user_id} due to timeout")

    except Exception as e:
        logger.error(f"Error during MFA auto-cancel: {e}", exc_info=True)
