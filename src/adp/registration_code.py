"""
Registration code delivery automation.

Sends personal registration codes to new hires via email.
"""

import logging

from playwright.async_api import Page

from src.adp.exceptions import FormSubmissionError
from src.adp.navigation import navigate_to_registration_codes, navigate_to_security_management
from src.adp.selectors.new_hire import (
    ASSOCIATE_ID_SEARCH_INPUT,
    CONFIRMATION_YES_BUTTON,
    EMPLOYEE_CHECKBOX,
    ISSUE_PRC_DROPDOWN,
    PERSONAL_EMAIL_OPTION,
    SEARCH_BUTTON,
)
from src.utils.screenshots import capture_screenshot

logger = logging.getLogger(__name__)


async def send_registration_code(page: Page, associate_id: str, email: str) -> None:
    """Send personal registration code to new hire's email.

    Args:
        page: Authenticated ADP page (should be on In-Progress Hires or dashboard).
        associate_id: The Associate ID captured from new hire form.
        email: New hire's personal email address.

    Raises:
        FormSubmissionError: If registration code delivery fails.
    """
    try:
        logger.info(f"Sending registration code to {email} for Associate ID {associate_id}")

        # Navigate to Security Management
        await navigate_to_security_management(page)

        # Navigate to Personal Registration Codes
        await navigate_to_registration_codes(page)

        # Search by Associate ID
        logger.info(f"Searching for Associate ID: {associate_id}")
        await page.wait_for_selector(ASSOCIATE_ID_SEARCH_INPUT, timeout=10000)
        await page.fill(ASSOCIATE_ID_SEARCH_INPUT, associate_id)
        await page.click(SEARCH_BUTTON)

        # Wait for results and select employee
        logger.info("Selecting employee from search results")
        await page.wait_for_selector(EMPLOYEE_CHECKBOX, timeout=10000)
        await page.click(EMPLOYEE_CHECKBOX)

        # Open Issue PRC dropdown
        logger.info("Opening Issue PRC dropdown")
        await page.wait_for_selector(ISSUE_PRC_DROPDOWN, timeout=10000)
        await page.click(ISSUE_PRC_DROPDOWN)

        # Select Personal Email Address option
        logger.info("Selecting Personal Email Address option")
        await page.wait_for_selector(PERSONAL_EMAIL_OPTION, timeout=10000)
        await page.click(PERSONAL_EMAIL_OPTION)

        # Confirm sending
        logger.info("Confirming registration code delivery")
        await page.wait_for_selector(CONFIRMATION_YES_BUTTON, timeout=10000)
        await page.click(CONFIRMATION_YES_BUTTON)

        # Wait for success (brief wait for the banner to appear)
        await page.wait_for_timeout(3000)

        logger.info(f"Successfully sent registration code to {email}")

    except Exception as e:
        logger.error(f"Failed to send registration code: {e}")
        screenshot_path = await capture_screenshot(page, "registration_code_error")
        raise FormSubmissionError(f"Failed to send registration code: {e}", screenshot_path)
