"""
Registration code delivery test.

Sends a personal registration code (PRC) to a new hire's email via
ADP's Security Management portal. Uses a known associate_id from a
prior live submit test.

Screenshots are taken at each major step for debugging.
"""

import asyncio
import os
import sys

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adp.auth import login_to_adp
from src.adp.navigation import navigate_to_registration_codes, navigate_to_security_management
from src.adp.selectors.new_hire import (
    ASSOCIATE_ID_SEARCH_INPUT,
    CONFIRMATION_YES_BUTTON,
    EMPLOYEE_CHECKBOX,
    ISSUE_PRC_DROPDOWN,
    PERSONAL_EMAIL_OPTION,
    SEARCH_BUTTON,
)
from src.config import settings


ASSOCIATE_ID = "57ZBGU74E"
EMAIL = "charles.annex830@slmails.com"
SS = "screenshots"  # screenshot directory


async def shot(page, filename: str) -> None:
    """Save a screenshot and print the path."""
    path = f"{SS}/{filename}"
    await page.screenshot(path=path)
    print(f"[SCREENSHOT] {path}")


async def main():
    """Test registration code delivery to a new hire's personal email."""
    print("=" * 80)
    print("REGISTRATION CODE DELIVERY TEST")
    print("=" * 80)

    # Confirmation prompt
    print(f"\nWARNING: This will send a registration code to {EMAIL}")
    input("Press Enter to continue or Ctrl+C to abort...")

    os.makedirs(SS, exist_ok=True)

    # Override headless for visibility
    original_headless = settings.headless
    settings.headless = False
    print("\n[INFO] Running with headless=False (browser will be visible)")

    pw = None
    browser = None

    try:
        # Step 1: Login
        print("\n[1] Logging into ADP...")
        creds = settings.get_adp_credentials(settings.telegram_allowed_user_ids[0])
        pw, browser, page, _ = await login_to_adp(
            username=creds.username,
            password=creds.password.get_secret_value(),
        )
        print("[OK] Login successful!")

        # Wait for dashboard to fully load before navigating
        print("[INFO] Waiting for dashboard to load...")
        await page.wait_for_timeout(15000)

        # Step 2: Navigate to Security Management
        print("\n[2] Navigating to Security Management (Setup menu)...")
        sec_page = await navigate_to_security_management(page)
        print("[OK] Security Management portal loaded!")

        # Screenshot 1: Security Management landing
        await shot(sec_page, "prc_step1_security_mgmt.png")

        # Step 3: Hover People menu (screenshot before click)
        print("\n[3] Hovering People menu...")
        from src.adp.selectors.new_hire import PEOPLE_MENU, PERSONAL_REGISTRATION_CODES_LINK
        await sec_page.wait_for_selector(PEOPLE_MENU, timeout=10000)
        await sec_page.hover(PEOPLE_MENU)
        await sec_page.wait_for_timeout(500)

        # Screenshot 2: People menu open
        await shot(sec_page, "prc_step2_people_menu.png")

        # Step 4: Click Personal Registration Codes
        print("[INFO] Clicking Personal Registration Codes...")
        await sec_page.wait_for_selector(PERSONAL_REGISTRATION_CODES_LINK, timeout=10000)
        await sec_page.click(PERSONAL_REGISTRATION_CODES_LINK)
        await sec_page.wait_for_selector('#empId', timeout=10000)
        print("[OK] Personal Registration Codes page loaded!")

        # Screenshot 3: PRC search page
        await shot(sec_page, "prc_step3_prc_page.png")

        # Step 5: Search by Associate ID
        print(f"\n[4] Searching for Associate ID: {ASSOCIATE_ID}...")
        await sec_page.wait_for_selector(ASSOCIATE_ID_SEARCH_INPUT, timeout=10000)
        await sec_page.fill(ASSOCIATE_ID_SEARCH_INPUT, ASSOCIATE_ID)
        await sec_page.click(SEARCH_BUTTON)
        await sec_page.wait_for_timeout(3000)

        # Screenshot 4: Search results
        await shot(sec_page, "prc_step4_search.png")

        # Step 6: Select employee checkbox
        print("[INFO] Selecting employee checkbox...")
        await sec_page.wait_for_selector(EMPLOYEE_CHECKBOX, timeout=10000)
        await sec_page.click(EMPLOYEE_CHECKBOX)
        await sec_page.wait_for_timeout(500)

        # Screenshot 5: Checkbox selected
        await shot(sec_page, "prc_step5_selected.png")

        # Step 7: Open Issue PRC dropdown
        print("[INFO] Clicking Issue PRC dropdown...")
        await sec_page.wait_for_selector(ISSUE_PRC_DROPDOWN, timeout=10000)
        await sec_page.click(ISSUE_PRC_DROPDOWN)
        await sec_page.wait_for_timeout(500)

        # Screenshot 6: Dropdown open
        await shot(sec_page, "prc_step6_dropdown.png")

        # Step 8: Select Personal Email Address
        print("[INFO] Selecting Personal Email Address...")
        await sec_page.wait_for_selector(PERSONAL_EMAIL_OPTION, timeout=10000)
        await sec_page.click(PERSONAL_EMAIL_OPTION)
        await sec_page.wait_for_timeout(1000)

        # Step 9: Confirm sending — Dojo popup with dynamic IDs, use stable selector
        print("[INFO] Waiting for confirmation popup to render...")
        await sec_page.wait_for_timeout(2000)

        print("[INFO] Clicking Yes on confirmation popup...")
        try:
            await sec_page.locator(CONFIRMATION_YES_BUTTON).click()
        except Exception as e:
            print(f"[WARNING] Primary Yes selector failed ({e}) -- trying JS fallback")
            await sec_page.evaluate("""() => {
                const buttons = document.querySelectorAll('span.dijitButtonText');
                for (const btn of buttons) {
                    if (btn.textContent.trim() === 'Yes') {
                        btn.closest('[role="button"]').click();
                        return true;
                    }
                }
                return false;
            }""")

        await sec_page.wait_for_timeout(3000)

        # Screenshot 7: After confirmation
        await shot(sec_page, "prc_after_confirm.png")

        print(f"\n[OK] Registration code sent successfully to {EMAIL}!")

        # Step 10: Wait for manual inspection
        print("\n[5] Waiting 30 seconds -- verify email was received...")
        for remaining in range(30, 0, -5):
            print(f"    Closing browser in {remaining} seconds...")
            await asyncio.sleep(5)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if browser:
            print("\n[6] Closing browser...")
            await browser.close()
            print("[OK] Browser closed")
        if pw:
            await pw.stop()

        settings.headless = original_headless

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
