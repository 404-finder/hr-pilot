"""
Shared form-filling utilities for ADP automation.

Provides reusable async functions for common form interactions.
"""

import logging
from typing import Optional

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def fill_text_field(page: Page, selector: str, value: str, timeout: int = 10000) -> None:
    """Clear and fill a text input field.

    Args:
        page: Playwright page object.
        selector: CSS selector for the input field.
        value: Text value to fill.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    await page.fill(selector, "")
    await page.fill(selector, value)
    logger.debug(f"Filled text field {selector} with value")


async def select_dropdown(page: Page, selector: str, value: str, timeout: int = 10000) -> None:
    """Select an option from a dropdown by visible text.

    Args:
        page: Playwright page object.
        selector: CSS selector for the dropdown.
        value: Visible text of the option to select.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    await page.select_option(selector, label=value)
    logger.debug(f"Selected dropdown {selector} with value: {value}")


async def fill_date_field(page: Page, selector: str, date_str: str, timeout: int = 10000) -> None:
    """Fill a date picker field (MM/DD/YYYY format).

    Args:
        page: Playwright page object.
        selector: CSS selector for the date field.
        date_str: Date string in MM/DD/YYYY format.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    await page.fill(selector, "")
    await page.fill(selector, date_str)
    await page.keyboard.press("Tab")  # Trigger date validation
    logger.debug(f"Filled date field {selector} with: {date_str}")


async def click_checkbox(page: Page, selector: str, should_check: bool, timeout: int = 10000) -> None:
    """Set a checkbox to checked or unchecked.

    Args:
        page: Playwright page object.
        selector: CSS selector for the checkbox.
        should_check: True to check, False to uncheck.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    is_checked = await page.is_checked(selector)
    if is_checked != should_check:
        await page.click(selector)
        logger.debug(f"Set checkbox {selector} to: {should_check}")


async def click_and_wait(
    page: Page,
    click_selector: str,
    wait_selector: str,
    click_timeout: int = 10000,
    wait_timeout: int = 10000,
) -> None:
    """Click a button and wait for the next element to appear.

    Args:
        page: Playwright page object.
        click_selector: CSS selector for the element to click.
        wait_selector: CSS selector for the element to wait for after clicking.
        click_timeout: Maximum wait time for click element in milliseconds.
        wait_timeout: Maximum wait time for next element in milliseconds.
    """
    await page.wait_for_selector(click_selector, timeout=click_timeout)
    await page.click(click_selector)
    logger.debug(f"Clicked {click_selector}")
    await page.wait_for_selector(wait_selector, timeout=wait_timeout)
    logger.debug(f"Waited for {wait_selector} to appear")


async def fill_react_dropdown(
    page: Page,
    selector: str,
    value: str,
    timeout: int = 10000
) -> None:
    """Fill a React Select dropdown by clicking, typing, and pressing Enter.

    Many ADP dropdowns use React Select components that require clicking
    the input, typing the value, waiting for options to load, then pressing Enter.

    Args:
        page: Playwright page object.
        selector: CSS selector for the dropdown input field.
        value: Value to type and select.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    await page.click(selector)
    logger.debug(f"Clicked React dropdown {selector}")
    await page.fill(selector, value)
    logger.debug(f"Typed value into React dropdown: {value}")
    await page.wait_for_timeout(1000)  # Wait for options to load
    await page.keyboard.press("Enter")
    logger.debug(f"Pressed Enter to select value in React dropdown {selector}")
