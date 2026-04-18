"""
Common bot handlers.

Handles /start, /help, /cancel, /debug commands and error handling.
"""

from telegram import Update
from telegram.ext import ContextTypes

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message."""
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        return

    welcome_message = """
Welcome to HR Pilot! 🤖

I can help you automate HR tasks in ADP Workforce Now.

Available commands:
/newhire - Add a new employee to ADP
/terminate - Process an employee termination
/help - Show detailed usage instructions
/cancel - Cancel current operation

Use /help to see the expected message formats.
"""
    await update.message.reply_text(welcome_message)
    logger.info(f"User {update.effective_user.id} started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show usage instructions."""
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        return

    help_message = """
📋 HR Pilot Usage Guide

**New Hire Command**
Format your message exactly like this:

/newhire
First Name: John
Last Name: Doe
Email: john.doe@company.com
Phone: 555-123-4567
Store Number: 39104
Job Title: Crew
Work Schedule: Part Time
Pay Rate: 15.50
Pay Type: hourly
Start Date: 03/01/2026
Reason: New Hire

**Field Options:**
• Store Number: **Texas:** 39101 (Hewitt Drive), 39102 (Interstate 35), 39103 (South Valley Mills), 39104 (North Valley Mills) — **Colorado:** 33561 (Austin Bluffs Pkwy), 33562 (Galley Rd), 33563 (Constitution Ave), 33564 (Cheyenne Meadows Rd), 33565 (Mesa Ridge Pkwy), 33566 (South Academy Blvd), 33567 (Stetson Hills Blvd)
• Job Title: assist manager, co-manager, crew, dist manager, gen manager, manager, sal manager
• Work Schedule: full time, part time
• Pay Type: hourly, salary
• Reason: current, new hire (optional, defaults to "new hire")

**Check Status Command**
Check if a new hire has completed their onboarding tasks:
/checkstatus First Last mm/dd/yyyy

Example: /checkstatus Carleton Haynes 03/01/2026
- First Last = employee's full name
- Date = "from" date filter for the onboarding dashboard

**Termination Command**
Format your message exactly like this:

/terminate
First Name: John
Last Name: Doe
Employee ID: 00123456
Termination Date: 03/15/2026
Last Work Date: 03/14/2026
Reason: Resignation
Type: Standard
Eligible for Rehire: Yes
Payout PTO: Yes
Notes: Employee accepted position at another company.

**Notes:**
- Dates must be in MM/DD/YYYY format
- Field names are case-insensitive
- Eligible for Rehire and Payout PTO must be "Yes" or "No"
"""
    await update.message.reply_text(help_message)
    logger.info(f"User {update.effective_user.id} requested help")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command - cancel current operation."""
    # Check authorization
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        return

    await update.message.reply_text("Operation cancelled.")
    logger.info(f"User {update.effective_user.id} cancelled operation")


async def debug_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /debug command.

    Args:
        update: Telegram update object.
        context: Telegram context object.
    """
    if update.effective_user.id not in settings.allowed_user_ids:
        await update.message.reply_text("Unauthorized")
        return

    await update.message.reply_text("Screenshots are no longer retained on disk.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)

    # Send error message to user if update is available
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Something went wrong. Please try again or contact support."
        )
