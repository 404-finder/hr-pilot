"""
Email change automation for in-progress hires.

Opens an in-progress hire in ADP, updates the email address,
and captures the Associate ID for subsequent PRC update.
"""

from playwright.async_api import Page

from src.adp.base_form import dismiss_pendo, fill_text_field
from src.adp.exceptions import FormSubmissionError
from src.adp.navigation import navigate_to_new_hire
from src.adp.selectors.new_hire import (
    IN_PROGRESS_SEARCH,
    IN_PROGRESS_TAB,
    PERSONAL_EMAIL_INPUT,
    SAVE_AND_EXIT_BUTTON,
)
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot

logger = setup_logger(__name__)


async def update_inprogress_email(
    page: Page, first_name: str, last_name: str, new_email: str
) -> dict:
    """Update email on an in-progress hire in ADP.

    Assumes already logged in and on the WFN dashboard. Navigates to the
    in-progress hire, updates the email field, scrapes the Associate ID,
    and saves.

    Args:
        page: Authenticated ADP page on the dashboard.
        first_name: Hire's first name (for matching).
        last_name: Hire's last name (used for search).
        new_email: New email address to set.

    Returns:
        Dict with associate_id, new_email, and screenshot_path.

    Raises:
        FormSubmissionError: If any step fails.
    """
    try:
        logger.info(f"Starting email change for {first_name} {last_name}")

        await dismiss_pendo(page)

        # ==================================================================
        # NAVIGATE TO HIRE/REHIRE PAGE
        # ==================================================================
        logger.info("Navigating to Hire/Rehire page")
        await navigate_to_new_hire(page)

        # ==================================================================
        # CLICK IN-PROGRESS HIRES TAB
        # ==================================================================
        logger.info("Clicking In-Progress Hires tab")
        await page.wait_for_selector(IN_PROGRESS_TAB, timeout=20000)
        await page.click(IN_PROGRESS_TAB)
        await page.wait_for_timeout(3000)

        # ==================================================================
        # SEARCH FOR HIRE BY LAST NAME
        # ==================================================================
        logger.info(f"Searching for in-progress hire: {last_name}")
        await page.wait_for_selector(IN_PROGRESS_SEARCH, timeout=20000)
        await page.fill(IN_PROGRESS_SEARCH, last_name)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # ==================================================================
        # CLICK MATCHING HIRE NAME
        # ==================================================================
        logger.info(f"Looking for matching hire: {last_name}")
        name_locator = page.locator(
            f'sdf-button:has(wfn-text:has-text("{last_name}"))'
        ).first

        try:
            await name_locator.wait_for(timeout=20000)
        except Exception:
            screenshot_path = await capture_screenshot(page, "email_change_not_found")
            raise FormSubmissionError(
                f"No in-progress hire found for '{last_name}'. "
                f"Check spelling or verify the hire exists in ADP.",
                screenshot_path,
            )

        await name_locator.click()
        logger.info(f"Clicked in-progress hire: {last_name}")

        # ==================================================================
        # WAIT FOR PERSONAL SECTION TO LOAD
        # ==================================================================
        logger.info("Waiting for Personal section to load")
        await page.wait_for_selector(PERSONAL_EMAIL_INPUT, timeout=20000)

        # Wait for form to become interactive (VPS latency)
        await page.wait_for_timeout(3000)

        # ==================================================================
        # SCRAPE ASSOCIATE ID
        # ==================================================================
        logger.info("Scraping Associate ID")
        try:
            associate_id = (
                await page.locator("div.headerLabelStyle:has-text('Associate ID')")
                .locator("xpath=following-sibling::div")
                .first.inner_text()
            )
            associate_id = associate_id.strip()
            logger.info(f"Captured Associate ID: {associate_id}")
        except Exception as e:
            logger.warning(f"Could not scrape Associate ID: {e}")
            associate_id = ""

        # ==================================================================
        # UPDATE EMAIL
        # ==================================================================
        logger.info(f"Updating email to: {new_email}")
        await fill_text_field(page, PERSONAL_EMAIL_INPUT, new_email)

        # Verify the email was filled
        actual_email = await page.input_value(PERSONAL_EMAIL_INPUT)
        if actual_email == new_email:
            logger.info(f"CONFIRMED: Email updated to '{new_email}'")
        else:
            logger.warning(
                f"Email field value '{actual_email}' does not match expected '{new_email}'"
            )

        # ==================================================================
        # TAKE REVIEW SCREENSHOT
        # ==================================================================
        screenshot_path = await capture_screenshot(page, "email_change_review")
        logger.info(f"Captured review screenshot: {screenshot_path}")

        # ==================================================================
        # SAVE AND EXIT
        # ==================================================================
        logger.info("Clicking Save and Exit")
        await page.wait_for_selector(SAVE_AND_EXIT_BUTTON, timeout=20000)
        await page.click(SAVE_AND_EXIT_BUTTON)

        # Wait for page to process the save
        await page.wait_for_timeout(5000)
        logger.info(f"Email change saved for {first_name} {last_name}")

        return {
            "associate_id": associate_id,
            "new_email": new_email,
            "screenshot_path": screenshot_path,
        }

    except FormSubmissionError:
        raise
    except Exception as e:
        logger.error(f"Failed to update in-progress email: {e}")
        screenshot_path = await capture_screenshot(page, "email_change_error")
        raise FormSubmissionError(
            f"Failed to update email for {first_name} {last_name}: {e}",
            screenshot_path,
        )


# REMOVE THIS BLOCK AFTER TESTING
if __name__ == "__main__":
    import asyncio
    import os
    import sys

    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )

    from src.adp.auth import login_to_adp
    from src.config import settings

    async def main():
        print("=" * 60)
        print("EMAIL CHANGE TEST")
        print("=" * 60)

        settings.headless = False
        browser = None

        try:
            # Login
            print("\n[1] Logging into ADP...")
            creds = settings.get_adp_credentials(settings.allowed_user_ids[0])
            browser, page, mfa_required = await login_to_adp(
                username=creds.username,
                password=creds.password.get_secret_value(),
            )

            if mfa_required:
                print("[MFA] ADP requires identity verification")
                code = input("Enter MFA code: ").strip()
                await page.get_by_label("Passcode").fill(code)
                try:
                    await page.get_by_role("button", name="Submit").click()
                except Exception:
                    await page.locator("[type='submit']").click()
                print("[MFA] Submitted, waiting for dashboard...")
                await page.wait_for_url(
                    "https://workforcenow.adp.com/**", timeout=30000
                )
                await page.wait_for_load_state("domcontentloaded")
                print("[OK] Dashboard loaded after MFA")

            # Update email
            print("\n[2] Updating in-progress hire email...")
            result = await update_inprogress_email(
                page,
                first_name="Ibrahim",
                last_name="Testme",
                new_email="charles.annex830@slmails.com",
            )

            print("\n" + "=" * 60)
            print("RESULT:")
            print(f"  Associate ID: {result['associate_id']}")
            print(f"  New Email:    {result['new_email']}")
            print(f"  Screenshot:   {result['screenshot_path']}")
            print("=" * 60)

            input("\nPress Enter to close browser...")

        except Exception as e:
            print(f"\n[FAIL] {e}")
            import traceback

            traceback.print_exc()
            input("\nPress Enter to close browser...")

        finally:
            if browser:
                await browser.close()
                print("[OK] Browser closed")

    asyncio.run(main())
