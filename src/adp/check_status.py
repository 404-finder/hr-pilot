"""
Onboarding status check automation.

Navigates the ADP Onboarding Dashboard to check a new hire's task completion
and captures screenshots of the status overview and uploaded documents.
"""

from playwright.async_api import Page

from src.adp.base_form import dismiss_pendo
from src.adp.exceptions import NavigationError
from src.adp.selectors.check_status import (
    EMPLOYEE_SEARCH_BOX,
    FROM_DATE_FIELD,
    UPLOAD_DOCS_VIEW_DETAILS,
    VIEW_BUTTON,
    VIEW_DASHBOARD_BUTTON,
    VIEW_EMPLOYEES_BUTTON,
)
from src.adp.selectors.new_hire import (
    HIRE_REHIRE_LINK,
    PROCESS_MENU_BUTTON,
)
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot

logger = setup_logger(__name__)


async def _navigate_to_onboarding_dashboard(page: Page) -> None:
    """Navigate from ADP dashboard to the Onboarding Dashboard.

    Path: Process → Hire/Rehire → View Dashboard

    Args:
        page: Authenticated ADP page.

    Raises:
        NavigationError: If navigation fails.
    """
    logger.info("Navigating to Onboarding Dashboard")

    # Wait for dashboard to fully load
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(15000)

    logger.info(f"Dashboard URL: {page.url}")

    # Dismiss Pendo overlay before clicking Process
    await dismiss_pendo(page)

    # Click Process menu
    logger.info("Clicking Process menu")
    await page.wait_for_selector(PROCESS_MENU_BUTTON, timeout=60000)
    await dismiss_pendo(page)
    await page.click(PROCESS_MENU_BUTTON)

    # Click Hire/Rehire link
    logger.info("Clicking Hire/Rehire link")
    await page.wait_for_selector(HIRE_REHIRE_LINK, timeout=20000)
    await page.click(HIRE_REHIRE_LINK)

    # Click View Dashboard button
    logger.info("Clicking View Dashboard button")
    await page.wait_for_selector(VIEW_DASHBOARD_BUTTON, timeout=20000)
    await page.click(VIEW_DASHBOARD_BUTTON)
    await page.wait_for_timeout(3000)

    # Wait for the dashboard to load
    await page.wait_for_selector(FROM_DATE_FIELD, timeout=20000)
    logger.info("Onboarding Dashboard loaded")


async def check_onboarding_status(
    page: Page, first_name: str, last_name: str, from_date: str
) -> dict:
    """Check onboarding status for an employee on the ADP Onboarding Dashboard.

    Navigates to the dashboard, filters by date, searches for the employee,
    and captures screenshots of the status overview and uploaded documents.

    Args:
        page: Authenticated ADP page.
        first_name: Employee's first name.
        last_name: Employee's last name.
        from_date: Date range filter start (mm/dd/yyyy).

    Returns:
        Dictionary with:
            - screenshots (list[str]): Paths to captured screenshots.
            - success (bool): Whether the check completed successfully.
            - error (str | None): Error message if failed.
    """
    screenshots = []

    try:
        # Step 1: Navigate to Onboarding Dashboard
        await _navigate_to_onboarding_dashboard(page)

        # Step 2: Set the "from" date
        logger.info(f"Setting from date: {from_date}")
        await page.click(FROM_DATE_FIELD, click_count=3)
        await page.type(FROM_DATE_FIELD, from_date)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(1000)

        # Click View button to reload with filtered data
        logger.info("Clicking View button")
        await page.wait_for_selector(VIEW_BUTTON, timeout=20000)
        await page.click(VIEW_BUTTON)
        await page.wait_for_timeout(3000)

        # Step 3: Open employee list
        logger.info("Opening employee list")
        await page.wait_for_selector(VIEW_EMPLOYEES_BUTTON, timeout=20000)
        await page.click(VIEW_EMPLOYEES_BUTTON)
        await page.wait_for_selector(EMPLOYEE_SEARCH_BOX, timeout=20000)

        # Step 4: Search for employee
        full_name = f"{first_name} {last_name}"
        logger.info(f"Searching for employee: {full_name}")
        # Multiple search boxes exist — use the one in the main content area (last/visible one)
        search_boxes = page.locator(EMPLOYEE_SEARCH_BOX)
        search_box = search_boxes.last
        await search_box.scroll_into_view_if_needed()
        await search_box.click()
        await search_box.fill(full_name)
        await page.wait_for_timeout(2000)

        # Click the employee button — try selectors in order
        employee_clicked = False
        employee_selectors = [
            f'sdf-button[id="Onboarding-Dashboard-OpenEmployeeStatus{first_name} {last_name}"]',
            f'sdf-button[aria-label="{first_name} {last_name}"]',
            f'sdf-button:has-text("{first_name} {last_name}")',
        ]
        for selector in employee_selectors:
            try:
                locator = page.locator(selector).first
                await locator.wait_for(state="visible", timeout=10000)
                await locator.scroll_into_view_if_needed()
                await locator.evaluate("el => el.click()")
                employee_clicked = True
                logger.info(f"Clicked employee via: {selector}")
                break
            except Exception as e:
                logger.info(f"Selector failed: {selector} — {e}")
                continue

        # Fallback: click via JS evaluate
        if not employee_clicked:
            try:
                logger.info("Trying JS click fallback")
                clicked = await page.evaluate(
                    """([firstName, lastName]) => {
                        const buttons = document.querySelectorAll('sdf-button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim().includes(firstName) && btn.textContent.trim().includes(lastName)) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }""",
                    [first_name, last_name]
                )
                if clicked:
                    employee_clicked = True
                    logger.info("Clicked employee via JS evaluate fallback")
            except Exception as e:
                logger.info(f"JS fallback failed: {e}")

        if not employee_clicked:
            raise NavigationError(
                f"Employee '{full_name}' not found in onboarding list"
            )

        await page.wait_for_timeout(3000)

        # Step 5: Screenshot #1 — Review Onboarding Status
        logger.info("Capturing Review Onboarding Status screenshot")
        await page.locator("text=Review Onboarding Status").wait_for(timeout=20000)
        path1 = await capture_screenshot(page, "check_status_overview")
        screenshots.append(path1)
        logger.info(f"Screenshot #1: {path1}")

        # Step 6: Click "View details" for Upload Documents row
        logger.info("Clicking View Details for Upload Documents")
        view_details_clicked = False

        # Primary selector
        try:
            await page.wait_for_selector(UPLOAD_DOCS_VIEW_DETAILS, timeout=5000)
            await page.click(UPLOAD_DOCS_VIEW_DETAILS)
            view_details_clicked = True
            logger.info("Clicked Upload Documents View Details via primary selector")
        except Exception:
            logger.info("Primary selector failed, trying fallback")

        # Fallback: find the row with "Upload Documents" text, then the View details button
        if not view_details_clicked:
            try:
                upload_row = page.locator('div[aria-label*="Upload Documents"]')
                view_btn = upload_row.locator('..').locator('sdf-button:has-text("View details")').first
                await view_btn.wait_for(timeout=5000)
                await view_btn.click()
                view_details_clicked = True
                logger.info("Clicked Upload Documents View Details via fallback")
            except Exception:
                logger.warning("Upload Documents View Details not found — no documents uploaded?")

        if not view_details_clicked:
            # Capture what we see and note the issue
            path_no_docs = await capture_screenshot(page, "check_status_no_upload_docs")
            screenshots.append(path_no_docs)
            logger.warning("Could not find Upload Documents View Details button")
            return {
                "screenshots": screenshots,
                "success": True,
                "error": "Upload Documents section not found — employee may not have uploaded documents yet.",
            }

        await page.wait_for_timeout(3000)

        # Step 7: Screenshot #2 — Uploaded Documents
        logger.info("Capturing Uploaded Documents screenshot")
        await page.get_by_role("heading", name="Uploaded Documents").wait_for(timeout=20000)
        path2 = await capture_screenshot(page, "check_status_documents")
        screenshots.append(path2)
        logger.info(f"Screenshot #2: {path2}")

        # Step 8: Return results
        return {
            "screenshots": screenshots,
            "success": True,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Check onboarding status failed: {e}", exc_info=True)

        # Capture error screenshot
        try:
            error_path = await capture_screenshot(page, "check_status_error")
            screenshots.append(error_path)
        except Exception as ss_err:
            logger.error(f"Error screenshot failed: {ss_err}")

        return {
            "screenshots": screenshots,
            "success": False,
            "error": str(e),
        }
