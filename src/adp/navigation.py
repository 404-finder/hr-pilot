"""
ADP navigation utilities.

Handles navigation through ADP menus and pages.
"""

from playwright.async_api import Page

from src.adp.base_form import dismiss_pendo
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
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot

logger = setup_logger(__name__)


async def _wait_for_process_button(page: Page) -> None:
    """Wait for the Process menu button with retry on failure.

    If the button isn't found after the initial timeout, captures a diagnostic
    screenshot, reloads the page, and tries once more.

    Args:
        page: Authenticated ADP page on the dashboard.

    Raises:
        NavigationError: If button not found after retry.
    """
    try:
        await page.wait_for_selector(PROCESS_MENU_BUTTON, timeout=60000)
        return
    except Exception:
        # Capture diagnostic screenshot to see what page we're actually on
        logger.warning(
            f"Process button not found. URL: {page.url} -- "
            "capturing diagnostic screenshot and retrying"
        )
        try:
            await capture_screenshot(page, "nav_debug_process_not_found")
        except Exception as ss_err:
            logger.warning(f"Diagnostic screenshot failed: {ss_err}")

        # Reload and retry once
        logger.info("Reloading page and retrying Process button wait")
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(15000)

        try:
            await page.wait_for_selector(PROCESS_MENU_BUTTON, timeout=60000)
        except Exception as retry_err:
            try:
                await capture_screenshot(page, "nav_debug_process_retry_failed")
            except Exception:
                pass
            raise NavigationError(
                f"Process button not found after reload. URL: {page.url}. "
                f"Error: {retry_err}"
            )


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

        # Wait for dashboard to fully load
        logger.info("Waiting for dashboard to load")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(15000)

        logger.info(f"Dashboard URL: {page.url}")

        # Click Process menu (with retry on failure)
        logger.info("Clicking Process menu")
        await _wait_for_process_button(page)
        await dismiss_pendo(page)
        await page.click(PROCESS_MENU_BUTTON)

        # Click Hire/Rehire link
        logger.info("Clicking Hire/Rehire link")
        await page.wait_for_selector(HIRE_REHIRE_LINK, timeout=20000)
        await page.click(HIRE_REHIRE_LINK)

        # Click Go to Hire button
        logger.info("Clicking Go to Hire button")
        await page.wait_for_selector(GO_TO_HIRE_BUTTON, timeout=20000)
        await page.click(GO_TO_HIRE_BUTTON)

        # Click HR PR New Hires card
        logger.info("Clicking HR PR New Hires card")
        await page.wait_for_selector(HR_PR_NEW_HIRES_CARD, timeout=20000)
        await page.click(HR_PR_NEW_HIRES_CARD)

        logger.info("Successfully navigated to New Hire form")

    except Exception as e:
        logger.error(f"Failed to navigate to New Hire form: {e}")
        raise NavigationError(f"Failed to navigate to New Hire form: {e}")


async def navigate_to_security_management(page: Page) -> Page:
    """Navigate from dashboard to Security Management portal.

    Navigation path: Setup → Security Management

    The Security Management link opens in a new browser tab. This function
    detects the new tab, waits for it to load, and returns it. Falls back
    to waiting on the current page if no new tab is detected.

    Args:
        page: Authenticated ADP page.

    Returns:
        The page (new tab or current) where Security Management loaded.

    Raises:
        NavigationError: If navigation fails.
    """
    try:
        logger.info("Navigating to Security Management")

        # Click Setup menu
        logger.info("Clicking Setup menu")
        await page.wait_for_selector(SETUP_MENU_BUTTON, timeout=20000)
        await page.click(SETUP_MENU_BUTTON)

        # Click Security Management — may open in a new tab
        logger.info("Clicking Security Management link")
        await page.wait_for_selector(SECURITY_MANAGEMENT_LINK, timeout=20000)

        new_page = None
        try:
            async with page.context.expect_page(timeout=10000) as new_page_info:
                await page.click(SECURITY_MANAGEMENT_LINK)
            new_page = await new_page_info.value
        except Exception:
            logger.info("No new tab detected for Security Management")

        if new_page is not None:
            await new_page.wait_for_load_state("load", timeout=60000)
            logger.info("Security Management opened in new tab -- switched to new tab")
            return new_page

        # No new tab — navigation happened in current page
        logger.info("Security Management loaded in current tab")
        await page.wait_for_load_state("load", timeout=60000)
        return page

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
        await page.wait_for_selector(PEOPLE_MENU, timeout=20000)
        await page.hover(PEOPLE_MENU)

        # Click Personal Registration Codes link
        logger.info("Clicking Personal Registration Codes link")
        await page.wait_for_selector(PERSONAL_REGISTRATION_CODES_LINK, timeout=20000)
        await page.click(PERSONAL_REGISTRATION_CODES_LINK)

        # Wait for search form to appear
        logger.info("Waiting for search form")
        await page.wait_for_selector('#empId', timeout=20000)

        logger.info("Successfully navigated to Personal Registration Codes")

    except Exception as e:
        logger.error(f"Failed to navigate to Personal Registration Codes: {e}")
        raise NavigationError(f"Failed to navigate to Personal Registration Codes: {e}")
