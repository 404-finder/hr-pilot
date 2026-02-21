"""
Debug screenshot utility.

Captures screenshots on error for troubleshooting ADP automation issues.
"""

import logging
import os
from datetime import datetime

from playwright.async_api import Page

from src.config import settings

logger = logging.getLogger(__name__)


async def capture_screenshot(page: Page, prefix: str) -> str:
    """Capture a debug screenshot on failure.

    Args:
        page: The Playwright page to screenshot.
        prefix: Filename prefix (e.g., 'new_hire_error').

    Returns:
        Path to the saved screenshot.
    """
    os.makedirs(settings.screenshot_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(settings.screenshot_dir, f"{prefix}_{timestamp}.png")

    await page.screenshot(path=path, full_page=True)
    logger.info(f"Screenshot captured: {path}")

    return path
