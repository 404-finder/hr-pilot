"""
Debug screenshot utility.

Captures screenshots to tempfiles and provides send-and-delete helpers
for Telegram delivery.
"""

import os
import tempfile

from playwright.async_api import Page
from telegram import Message

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def capture_screenshot(page: Page, prefix: str) -> str:
    """Capture a debug screenshot to a temporary file.

    Args:
        page: The Playwright page to screenshot.
        prefix: Filename prefix (e.g., 'new_hire_error').

    Returns:
        Path to the saved temporary screenshot.
    """
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".png", prefix=f"{prefix}_"
    )
    tmp.close()

    await page.screenshot(path=tmp.name, full_page=False, timeout=60000)
    logger.info(f"Screenshot captured: {tmp.name}")

    return tmp.name


async def send_and_delete_screenshot(
    message: Message, path: str, caption: str
) -> None:
    """Send a screenshot via Telegram and delete the file.

    Args:
        message: Telegram Message to reply on.
        path: Path to the screenshot file.
        caption: Caption for the photo message.
    """
    try:
        with open(path, "rb") as f:
            await message.reply_photo(photo=f, caption=caption)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
