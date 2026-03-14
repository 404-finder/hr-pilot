"""
ADP authentication module.

Handles login/logout and session management for ADP Workforce Now.
"""

import asyncio
import logging
from typing import Tuple

from playwright.async_api import Browser, Page, async_playwright

from src.adp.exceptions import LoginError
from src.adp.selectors.login import (
    NEXT_BUTTON,
    PASSWORD_INPUT,
    REMIND_ME_LATER_BUTTON,
    SIGN_IN_BUTTON,
    USERNAME_INPUT,
)
from src.config import settings

logger = logging.getLogger(__name__)


async def login_to_adp(username: str, password: str) -> Tuple[Browser, Page]:
    """Log into ADP WFN and return the authenticated browser and page.

    Implements retry logic with exponential backoff (3 attempts: 2s, 4s, 8s).

    Args:
        username: ADP username.
        password: ADP password (plaintext).

    Returns:
        Tuple of (Browser, Page) - authenticated Playwright browser and page.

    Raises:
        LoginError: If login fails after max retries.
    """
    max_retries = 3
    backoff_delays = [2, 4, 8]  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"ADP login attempt {attempt}/{max_retries}")

            # Launch browser
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=settings.headless)
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to login page
            logger.info(f"Navigating to ADP login URL")
            await page.goto(settings.adp_login_url, timeout=30000)

            # Fill username and click next
            logger.info("Entering username")
            await page.wait_for_selector(USERNAME_INPUT, timeout=10000)
            await page.fill(USERNAME_INPUT, username)
            await page.click(NEXT_BUTTON)

            # Wait for password field to appear
            logger.info("Waiting for password field")
            await page.wait_for_selector(PASSWORD_INPUT, timeout=10000)

            # Fill password and sign in
            logger.info("Entering password")
            await page.fill(PASSWORD_INPUT, password)
            await page.click(SIGN_IN_BUTTON)

            # Wait for successful redirect to WFN dashboard
            logger.info("Waiting for redirect to Workforce Now")
            await page.wait_for_url("**/workforcenow.adp.com/**", timeout=30000)

            # Try to dismiss popup if it appears
            try:
                logger.info("Checking for ADP popup")
                await page.wait_for_selector(REMIND_ME_LATER_BUTTON, timeout=5000)
                await page.click(REMIND_ME_LATER_BUTTON)
                logger.info("Dismissed ADP popup")
            except Exception:
                logger.info("No popup detected")

            logger.info("Successfully logged into ADP")
            return browser, page

        except Exception as e:
            logger.error(f"Login attempt {attempt} failed: {e}")

            # Close browser if it was opened
            try:
                await browser.close()
            except Exception:
                pass

            # If this was the last attempt, raise LoginError
            if attempt == max_retries:
                raise LoginError(f"Failed to login to ADP after {max_retries} attempts: {e}")

            # Otherwise, wait before retrying
            delay = backoff_delays[attempt - 1]
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)

    # This should never be reached due to the raise above, but for type safety
    raise LoginError(f"Failed to login to ADP after {max_retries} attempts")
