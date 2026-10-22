"""
New hire command handler.

Handles /newhire: fills the form, saves it, sends the PRC, and reports back.
"""

from typing import Optional

from telegram import Message, Update
from telegram.ext import ContextTypes

from src.adp.auth import login_to_adp
from src.adp.navigation import navigate_to_new_hire
from src.adp.new_hire_form import fill_new_hire_form
from src.adp.registration_code import send_registration_code
from src.config import settings
from src.telegram_bot.parsers import parse_new_hire, parse_new_hire_raw
from src.telegram_bot.watchdog import start_watchdog, stop_watchdog
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot, send_and_delete_screenshot
from src.validators import validate_new_hire_input

logger = setup_logger(__name__)


async def _cleanup_session(context: ContextTypes.DEFAULT_TYPE, browser, pw) -> None:
    """Stop the watchdog, close the browser, stop Playwright, and clear session state.

    Safe to call with None values and more than once.

    Args:
        context: Telegram context object.
        browser: Playwright browser (or None).
        pw: Playwright instance (or None).
    """
    stop_watchdog(context)
    if browser:
        try:
            await browser.close()
            logger.info("Browser closed")
        except Exception as close_error:
            logger.error(f"Error closing browser: {close_error}")
    if pw:
        try:
            await pw.stop()
            logger.info("Playwright stopped")
        except Exception as pw_error:
            logger.error(f"Error stopping Playwright: {pw_error}")

    context.user_data.pop("pw", None)
    context.user_data.pop("browser", None)
    context.user_data.pop("page", None)
    context.user_data.pop("hire", None)
    context.user_data.pop("awaiting_mfa_code", None)


async def _send_screenshot(message: Message, path: Optional[str], caption: str) -> None:
    """Send a screenshot if one exists, logging (not raising) on failure.

    Args:
        message: Telegram Message to reply on.
        path: Path to the screenshot file, or None to skip.
        caption: Caption for the photo message.
    """
    if not path:
        return
    try:
        await send_and_delete_screenshot(message, path, caption)
    except Exception as screenshot_error:
        logger.error(f"Failed to send screenshot '{caption}': {screenshot_error}")


def _format_summary(
    hire,
    associate_id: str,
    warnings: list[str],
    prc_error: Optional[Exception] = None,
) -> str:
    """Build the final status message, with warnings listed first.

    Args:
        hire: Validated NewHire model instance.
        associate_id: Associate ID captured from the form.
        warnings: Non-fatal issues raised during form fill.
        prc_error: Exception from the PRC step, or None on success.

    Returns:
        Formatted Telegram message text.
    """
    parts = []
    if warnings:
        parts.append(
            "⚠️ CHECK DURING ADP REVIEW:\n" + "\n".join(f"  - {w}" for w in warnings)
        )

    if prc_error is None:
        parts.append(
            f"[OK] New hire saved: {hire.first_name} {hire.last_name}\n"
            f"Associate ID: {associate_id}\n"
            f"PRC sent to: {hire.email}"
        )
    else:
        parts.append(
            f"[PARTIAL] Form SAVED for {hire.first_name} {hire.last_name}, "
            f"but PRC was NOT sent.\n"
            f"Associate ID: {associate_id}\n"
            f"Send the PRC manually: ADP → Security Management → "
            f"Personal Registration Codes.\n"
            f"Error: {prc_error}"
        )

    return "\n\n".join(parts)


async def _run_new_hire_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pw,
    browser,
    page,
    hire,
) -> None:
    """Navigate ADP, fill and save the new hire form, send the PRC, and report.

    Shared by both the non-MFA path (called directly from handle_new_hire)
    and the MFA path (called from handle_mfa_code after code verification).
    Never raises; always cleans up the browser session before returning.

    Args:
        update: Telegram update object.
        context: Telegram context object.
        pw: Playwright instance.
        browser: Authenticated Playwright browser.
        page: Authenticated ADP page.
        hire: Validated NewHire model instance.
    """
    try:
        # --- Step 1: Fill + Save & Exit ---
        try:
            logger.info("Navigating to new hire form")
            await navigate_to_new_hire(page)

            logger.info("Filling and saving new hire form")
            result = await fill_new_hire_form(page, hire, dry_run=False)
        except Exception as e:
            logger.error(f"Error processing new hire: {e}", exc_info=True)
            await update.message.reply_text(f"[FAIL] Error processing new hire:\n{str(e)}")
            await _send_screenshot(
                update.message, getattr(e, "screenshot_path", None), "Debug screenshot"
            )
            return

        associate_id = result["associate_id"]
        warnings = result.get("warnings", [])
        logger.info(f"Form saved for {hire.first_name} {hire.last_name} ({associate_id})")

        await _send_screenshot(
            update.message,
            result.get("review_screenshot_path"),
            f"Filled form (pre-save): {hire.first_name} {hire.last_name}",
        )
        await _send_screenshot(
            update.message,
            result.get("screenshot_path"),
            f"[OK] Saved: {hire.first_name} {hire.last_name} ({associate_id})",
        )

        # --- Step 2: Registration Code ---
        try:
            logger.info(f"Sending registration code for Associate ID: {associate_id}")
            prc_screenshot = await send_registration_code(page, associate_id, hire.email)

        except Exception as e:
            logger.warning(f"Registration code failed: {e}", exc_info=True)
            await update.message.reply_text(
                _format_summary(hire, associate_id, warnings, prc_error=e)
            )
            await _send_screenshot(
                update.message, getattr(e, "screenshot_path", None), "PRC error screenshot"
            )

        else:
            await _send_screenshot(
                update.message, prc_screenshot, f"[OK] Registration code sent to {hire.email}"
            )
            await update.message.reply_text(_format_summary(hire, associate_id, warnings))
            logger.info(f"New hire complete for {hire.first_name} {hire.last_name}")

    except Exception as e:
        # Telegram send failures etc. — never let them skip cleanup
        logger.error(f"Unexpected error in new hire flow: {e}", exc_info=True)

    finally:
        await _cleanup_session(context, browser, pw)


async def handle_new_hire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newhire command.

    Parses the message, logs into ADP, fills and saves the form,
    sends the PRC, and reports the result.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized new hire attempt from user {update.effective_user.id}")
        return

    pw = None
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

        # Start watchdog timer for long-running operation
        await start_watchdog(context, update.effective_chat.id, "New hire processing")

        # Log into ADP
        logger.info("Logging into ADP")
        pw, browser, page, mfa_required = await login_to_adp(
            username=adp_creds.username,
            password=adp_creds.password.get_secret_value(),
        )

        if mfa_required:
            # Store state and wait for user to supply the MFA code
            context.user_data["awaiting_mfa_code"] = True
            context.user_data["pw"] = pw
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

        # No MFA — proceed directly (flow handles its own errors and cleanup)
        await _run_new_hire_flow(update, context, pw, browser, page, hire)

    except ValueError as e:
        # Parsing error
        error_message = f"[FAIL] Invalid message format:\n{str(e)}\n\nUse /help to see the expected format."
        await update.message.reply_text(error_message)
        logger.error(f"Parsing error: {e}")
        await _cleanup_session(context, browser, pw)

    except Exception as e:
        # ADP automation error (login)
        logger.error(f"Error processing new hire: {e}", exc_info=True)
        error_message = f"[FAIL] Error processing new hire:\n{str(e)}"
        await update.message.reply_text(error_message)
        await _send_screenshot(
            update.message, getattr(e, "screenshot_path", None), "Debug screenshot"
        )
        await _cleanup_session(context, browser, pw)


async def handle_cancel_hire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command to abort an operation waiting on an MFA code.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        return

    if not context.user_data.get("awaiting_mfa_code"):
        await update.message.reply_text("Nothing to cancel.")
        return

    try:
        # Pops awaiting_mfa_code, so auto_cancel_mfa becomes a no-op
        await _cleanup_session(
            context, context.user_data.get("browser"), context.user_data.get("pw")
        )
        context.user_data.pop("check_status_params", None)

        await update.message.reply_text("[FAIL] Cancelled. Browser closed.")
        logger.info("MFA wait cancelled by user")

    except Exception as e:
        logger.error(f"Error cancelling operation: {e}", exc_info=True)
        await update.message.reply_text(f"Error during cancellation: {str(e)}")


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
            raise Exception("Could not find Submit button on MFA page")

        # Wait for dashboard redirect after successful verification
        logger.info("Waiting for dashboard after MFA verification")
        await page.wait_for_url("https://workforcenow.adp.com/**", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        logger.info(f"Post-MFA URL: {page.url}")

        # Dismiss passkey/reminder popup if it appears
        try:
            from src.adp.selectors.login import REMIND_ME_LATER_BUTTON
            remind_btn = page.locator(REMIND_ME_LATER_BUTTON)
            if await remind_btn.is_visible():
                await remind_btn.click()
                logger.info("Dismissed post-MFA popup")
                await page.wait_for_timeout(2000)
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
        stop_watchdog(context)
        logger.error(f"MFA verification failed: {e}", exc_info=True)

        mfa_screenshot = None
        try:
            mfa_screenshot = await capture_screenshot(page, "mfa_verification_error")
        except Exception:
            pass

        await update.message.reply_text(
            f"[FAIL] MFA verification failed:\n{str(e)}\n\n"
            "Please try again."
        )
        await _send_screenshot(update.message, mfa_screenshot, "MFA error screenshot")

        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        pw = context.user_data.get("pw")
        if pw:
            try:
                await pw.stop()
                logger.info("Playwright stopped")
            except Exception as pw_error:
                logger.error(f"Error stopping Playwright: {pw_error}")

        context.user_data.pop("pw", None)
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
            stop_watchdog(context)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            pw = context.user_data.get("pw")
            if pw:
                try:
                    await pw.stop()
                    logger.info("Playwright stopped")
                except Exception as pw_error:
                    logger.error(f"Error stopping Playwright: {pw_error}")
            context.user_data.pop("pw", None)
            context.user_data.pop("browser", None)
            context.user_data.pop("page", None)
        return

    # New hire flow (handles its own errors and cleanup)
    await _run_new_hire_flow(
        update, context, context.user_data.get("pw"), browser, page, hire
    )


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
        pw = context.user_data.get("pw")
        if pw:
            try:
                await pw.stop()
                logger.info("Playwright stopped")
            except Exception as pw_error:
                logger.error(f"Error stopping Playwright: {pw_error}")

        context.user_data.pop("awaiting_mfa_code", None)
        stop_watchdog(context)
        context.user_data.pop("pw", None)
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
