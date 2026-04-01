"""
Check status command handler.

Handles /checkstatus command to check onboarding task completion in ADP.
"""

import glob
import os
import re

from telegram import Update
from telegram.ext import ContextTypes

from src.adp.auth import login_to_adp
from src.adp.check_status import check_onboarding_status
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot

logger = setup_logger(__name__)


def parse_check_status(message_text: str) -> dict:
    """Parse '/checkstatus First Last mm/dd/yyyy' into components.

    Args:
        message_text: Raw Telegram message text.

    Returns:
        Dictionary with first_name, last_name, and from_date.

    Raises:
        ValueError: If format is wrong.
    """
    # Strip the command prefix
    text = message_text.strip()
    if text.lower().startswith("/checkstatus"):
        text = text[len("/checkstatus"):].strip()

    parts = text.split()
    if len(parts) != 3:
        raise ValueError(
            "Expected 3 parts: First Last mm/dd/yyyy"
        )

    first_name, last_name, from_date = parts

    # Validate date format
    if not re.match(r"^\d{2}/\d{2}/\d{4}$", from_date):
        raise ValueError(
            f"Invalid date format '{from_date}'. Expected mm/dd/yyyy"
        )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "from_date": from_date,
    }


async def handle_check_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /checkstatus command to check onboarding status in ADP.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized check status attempt from user {update.effective_user.id}")
        return

    pw = None
    browser = None

    try:
        # Parse message
        parsed = parse_check_status(update.message.text)
        first_name = parsed["first_name"]
        last_name = parsed["last_name"]
        from_date = parsed["from_date"]
        logger.info(f"Check status: {first_name} {last_name}, from {from_date}")

    except ValueError as e:
        await update.message.reply_text(
            f"[FAIL] {e}\n\nUsage: /checkstatus First Last mm/dd/yyyy"
        )
        return

    try:
        # Send processing message
        await update.message.reply_text(
            f"Checking onboarding status for {first_name} {last_name}..."
        )

        # Get ADP credentials
        try:
            adp_creds = settings.get_adp_credentials(update.effective_user.id)
        except ValueError as creds_error:
            await update.message.reply_text(f"[FAIL] {creds_error}")
            logger.error(f"Credentials lookup failed: {creds_error}")
            return

        # Log into ADP
        logger.info("Logging into ADP")
        pw, browser, page, mfa_required = await login_to_adp(
            username=adp_creds.username,
            password=adp_creds.password.get_secret_value(),
        )

        if mfa_required:
            # Store state for MFA relay
            context.user_data["awaiting_mfa_code"] = True
            context.user_data["pw"] = pw
            context.user_data["browser"] = browser
            context.user_data["page"] = page
            context.user_data["check_status_params"] = parsed

            if context.job_queue:
                context.job_queue.run_once(
                    _auto_cancel_check_status_mfa,
                    180,  # 3 minutes
                    chat_id=update.effective_chat.id,
                    user_id=update.effective_user.id,
                    data={"user_id": update.effective_user.id},
                )

            await update.message.reply_text(
                "ADP requires identity verification.\n"
                "A text message has been sent to your phone.\n\n"
                "Please reply with the verification code."
            )
            logger.info("MFA required — waiting for user to supply code")
            return

        # No MFA — run check directly
        await _run_check_status(update, context, browser, page, parsed)

    except Exception as e:
        logger.error(f"Error checking onboarding status: {e}", exc_info=True)
        await update.message.reply_text(f"[FAIL] Error checking status:\n{str(e)}")

        # Send most recent screenshot for debugging
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

    finally:
        # Close browser if not handed off to MFA
        if browser and not context.user_data.get("awaiting_mfa_code"):
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


async def _run_check_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    browser,
    page,
    params: dict,
) -> None:
    """Run the onboarding status check and send screenshots.

    Args:
        update: Telegram update object.
        context: Telegram context object.
        browser: Playwright browser instance.
        page: Authenticated ADP page.
        params: Parsed check status parameters.
    """
    result = await check_onboarding_status(
        page,
        params["first_name"],
        params["last_name"],
        params["from_date"],
    )

    # Send all captured screenshots
    for path in result["screenshots"]:
        try:
            with open(path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=os.path.basename(path),
                )
        except Exception as send_err:
            logger.error(f"Failed to send screenshot {path}: {send_err}")

    # Send status message
    if result["success"]:
        msg = f"[OK] Onboarding status check complete for {params['first_name']} {params['last_name']}."
        if result.get("error"):
            msg += f"\nNote: {result['error']}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(
            f"[FAIL] Check failed: {result['error']}"
        )


async def _auto_cancel_check_status_mfa(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Auto-cancel MFA for check status after 3 minutes.

    Args:
        context: Telegram context object.
    """
    job = context.job
    user_id = job.data.get("user_id")

    if not context.user_data.get("awaiting_mfa_code"):
        return

    try:
        browser = context.user_data.get("browser")
        if browser:
            await browser.close()
            logger.info("Browser closed after check status MFA timeout")
        pw = context.user_data.get("pw")
        if pw:
            try:
                await pw.stop()
                logger.info("Playwright stopped")
            except Exception as pw_error:
                logger.error(f"Error stopping Playwright: {pw_error}")

        context.user_data.pop("awaiting_mfa_code", None)
        context.user_data.pop("pw", None)
        context.user_data.pop("browser", None)
        context.user_data.pop("page", None)
        context.user_data.pop("check_status_params", None)

        await context.bot.send_message(
            chat_id=job.chat_id,
            text=(
                "[WARNING] MFA verification timed out after 3 minutes. "
                "Please try again with /checkstatus."
            ),
        )
        logger.info(f"Auto-cancelled check status MFA for user {user_id}")

    except Exception as e:
        logger.error(f"Error during check status MFA auto-cancel: {e}", exc_info=True)
