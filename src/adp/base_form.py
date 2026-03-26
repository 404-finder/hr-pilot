"""
Shared form-filling utilities for ADP automation.

Provides reusable async functions for common form interactions.
"""

from typing import Optional

from playwright.async_api import Page

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def dismiss_pendo(page: Page) -> None:
    """Dismiss any Pendo product-tour overlay that may be blocking clicks.

    Tries a close button first; falls back to removing all Pendo elements via
    JavaScript. Silently no-ops if no Pendo overlay is present.

    Args:
        page: Playwright page object.
    """
    try:
        # if not await page.locator("[id^='pendo-']").first.is_visible():
        if await page.locator("[id^='pendo-']").count() == 0:
            return

        logger.info("Pendo overlay detected — attempting dismissal")
        dismissed = False
        for sel in ["[id^='pendo-close']", "button._pendo-close-guide"]:
            try:
                await page.locator(sel).click(timeout=2000)
                dismissed = True
                logger.info(f"Pendo dismissed via close button: {sel}")
                break
            except Exception:
                continue

        if not dismissed:
            await page.evaluate(
                "document.querySelectorAll('[id^=\"pendo-\"]').forEach(el => el.remove())"
            )
            logger.info("Pendo overlay removed via JavaScript")

        await page.wait_for_timeout(1000)
    except Exception:
        pass  # No Pendo overlay present


async def fill_text_field(
    page: Page, selector: str, value: str, timeout: int = 20000
) -> None:
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


async def select_dropdown(
    page: Page, selector: str, value: str, timeout: int = 20000
) -> None:
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


async def fill_date_field(
    page: Page, selector: str, date_str: str, timeout: int = 20000
) -> None:
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


async def click_checkbox(
    page: Page, selector: str, should_check: bool, timeout: int = 20000
) -> None:
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
    click_timeout: int = 20000,
    wait_timeout: int = 20000,
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


async def fill_mdf_dropdown(
    page: Page,
    selector: str,
    search_code: str,
    match_text: str,
    timeout: int = 20000,
) -> None:
    """Fill an ADP MDFSelectBox React Select dropdown.

    ADP uses MDFSelectBox (a React Select variant) for most dropdowns.
    These require clicking to open, typing a short code to filter options,
    waiting for the list to load, then clicking the matching option.

    Args:
        page: Playwright page object.
        selector: CSS selector for the dropdown input element.
        search_code: Short prefix to type to filter options (e.g., "BE").
        match_text: Unique substring to identify the correct option.
        timeout: Maximum wait time in milliseconds.
    """
    await page.wait_for_selector(selector, timeout=timeout)
    await page.click(selector)
    await page.fill(selector, search_code)
    logger.debug(f"MDF dropdown {selector}: typed '{search_code}'")
    await page.wait_for_timeout(1500)
    option_selector = f'[class*="MDFSelectBox__option"]:has-text("{match_text}")'
    await page.wait_for_selector(option_selector, timeout=timeout)
    await page.click(option_selector)
    await page.wait_for_timeout(500)
    logger.debug(f"MDF dropdown {selector}: selected '{match_text}'")


async def click_visible_next_button(page: Page, timeout: int = 20000) -> None:
    """Click the first visible primary Next button in the current form section.

    ADP's new hire form keeps Next buttons from all sections in the DOM
    simultaneously. Playwright's standard selectors pick the first by DOM
    order (often a hidden section's button). This helper uses JavaScript to
    find and click only the currently visible Next button.

    Args:
        page: Playwright page object.
        timeout: Max wait time (ms) for a visible button to appear.

    Raises:
        Exception: If no visible primary Next button is found within timeout.
    """
    start = page._impl_obj._loop.time()
    deadline = start + timeout / 1000
    while True:
        clicked = await page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll("button.vdl-button--primary"));
            const btn = buttons.find(b =>
                b.textContent.trim() === "Next" &&
                b.offsetParent !== null &&
                !b.disabled
            );
            if (btn) { btn.click(); return true; }
            return false;
        }""")
        if clicked:
            logger.debug("Clicked visible primary Next button")
            return
        if page._impl_obj._loop.time() >= deadline:
            raise Exception("No visible primary Next button found within timeout")
        await page.wait_for_timeout(500)


async def fill_react_dropdown(
    page: Page, selector: str, value: str, timeout: int = 20000
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
