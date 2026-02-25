"""
ADP navigation utilities.

Handles navigation through ADP menus and pages.
"""

import logging

from playwright.async_api import Page

from src.adp.base_form import click_and_wait
from src.adp.exceptions import NavigationError
from src.adp.selectors.new_hire import (
    GO_TO_HIRE_BUTTON,
    HIRE_REHIRE_LINK,
    HR_PR_NEW_HIRES_CARD,
    PEOPLE_MENU,
    PERSONAL_REGISTRATION_CODES_LINK,
    PROCESS_MENU_BUTTON,
    SECURITY_MANAGEMENT_LINK,
    SETUP_MENU_BUTTON,
)

logger = logging.getLogger(__name__)


async def navigate_to_new_hire(page: Page) -> None:
    """Navigate from ADP dashboard to the Add New Hire page.

    Navigation path: Process → Hire/Rehire → Go to Hire → HR PR New Hires

    Args:
        page: Authenticated ADP page.

    Raises:
        NavigationError: If navigation fails.
    """
    try:
        logger.info("Navigating to New Hire form")

        # Wait for dashboard to fully load (ADP is slow)
        logger.info("Waiting for dashboard to fully load")
        await page.wait_for_timeout(15000)

        # Click Process menu
        logger.info("Clicking Process menu")
        await page.wait_for_selector(PROCESS_MENU_BUTTON, timeout=30000)
        await page.click(PROCESS_MENU_BUTTON)

        # Click Hire/Rehire link
        logger.info("Clicking Hire/Rehire link")
        await page.wait_for_selector(HIRE_REHIRE_LINK, timeout=10000)
        await page.click(HIRE_REHIRE_LINK)

        # Click Go to Hire button
        logger.info("Clicking Go to Hire button")
        await page.wait_for_selector(GO_TO_HIRE_BUTTON, timeout=10000)
        await page.click(GO_TO_HIRE_BUTTON)

        # Click HR PR New Hires card
        logger.info("Clicking HR PR New Hires card")
        await page.wait_for_selector(HR_PR_NEW_HIRES_CARD, timeout=10000)
        await page.click(HR_PR_NEW_HIRES_CARD)

        logger.info("Successfully navigated to New Hire form")

    except Exception as e:
        logger.error(f"Failed to navigate to New Hire form: {e}")
        raise NavigationError(f"Failed to navigate to New Hire form: {e}")


async def navigate_to_security_management(page: Page) -> None:
    """Navigate from dashboard to Security Management portal.

    Navigation path: Setup → Security Management

    Args:
        page: Authenticated ADP page.

    Raises:
        NavigationError: If navigation fails.
    """
    try:
        logger.info("Navigating to Security Management")

        # Click Setup menu
        logger.info("Clicking Setup menu")
        await page.wait_for_selector(SETUP_MENU_BUTTON, timeout=10000)
        await page.click(SETUP_MENU_BUTTON)

        # Click Security Management link
        logger.info("Clicking Security Management link")
        await page.wait_for_selector(SECURITY_MANAGEMENT_LINK, timeout=10000)
        await page.click(SECURITY_MANAGEMENT_LINK)

        # Wait for redirect to netsecure.adp.com
        logger.info("Waiting for redirect to Security Management portal")
        await page.wait_for_url("**/netsecure.adp.com/**", timeout=30000)

        logger.info("Successfully navigated to Security Management")

    except Exception as e:
        logger.error(f"Failed to navigate to Security Management: {e}")
        raise NavigationError(f"Failed to navigate to Security Management: {e}")


async def navigate_to_registration_codes(page: Page) -> None:
    """Navigate to Personal Registration Codes in Security Management.

    Navigation path: People (hover) → Personal Registration Codes

    Args:
        page: Page already on Security Management portal.

    Raises:
        NavigationError: If navigation fails.
    """
    try:
        logger.info("Navigating to Personal Registration Codes")

        # Hover over People menu
        logger.info("Hovering over People menu")
        await page.wait_for_selector(PEOPLE_MENU, timeout=10000)
        await page.hover(PEOPLE_MENU)

        # Click Personal Registration Codes link
        logger.info("Clicking Personal Registration Codes link")
        await page.wait_for_selector(PERSONAL_REGISTRATION_CODES_LINK, timeout=10000)
        await page.click(PERSONAL_REGISTRATION_CODES_LINK)

        # Wait for search form to appear
        logger.info("Waiting for search form")
        await page.wait_for_selector('#empId', timeout=10000)

        logger.info("Successfully navigated to Personal Registration Codes")

    except Exception as e:
        logger.error(f"Failed to navigate to Personal Registration Codes: {e}")
        raise NavigationError(f"Failed to navigate to Personal Registration Codes: {e}")
