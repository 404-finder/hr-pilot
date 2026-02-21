"""
Test script for ADP login and navigation.

Logs into ADP, captures dashboard screenshot, and allows manual inspection.
"""

import asyncio
import os
import sys

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adp.auth import login_to_adp
from src.adp.selectors.new_hire import (
    FIRST_NAME_INPUT,
    GO_TO_HIRE_BUTTON,
    HIRE_REHIRE_LINK,
    HR_PR_NEW_HIRES_CARD,
    LAST_NAME_INPUT,
    PROCESS_MENU_BUTTON,
)
from src.config import settings


async def main():
    """Test ADP login and navigation."""
    print("=" * 60)
    print("ADP Login and Navigation Test")
    print("=" * 60)

    browser = None

    try:
        # Step 1-4: Login to ADP
        print("\n[1] Logging into ADP...")
        browser, page = await login_to_adp()
        print("[OK] Login successful!")

        # Step 5: Wait for dashboard to fully load
        print("\n[2] Waiting 10 seconds for dashboard to fully load...")
        await asyncio.sleep(10)

        # Step 6: Take screenshot
        print("\n[3] Capturing dashboard screenshot...")
        screenshot_dir = settings.screenshot_dir
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, "dashboard.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[OK] Screenshot saved to: {screenshot_path}")

        # Step 7: Print current URL
        print("\n[4] Current URL:")
        print(f"    {page.url}")

        # Step 8: Print page title
        print("\n[5] Page Title:")
        title = await page.title()
        print(f"    {title}")

        # Step 9: Check for Process button
        print("\n[6] Checking for Process button...")
        try:
            process_button = await page.wait_for_selector(
                PROCESS_MENU_BUTTON,
                timeout=5000
            )
            if process_button:
                print(f"[OK] Process button FOUND: {PROCESS_MENU_BUTTON}")
            else:
                print(f"[FAIL] Process button NOT found: {PROCESS_MENU_BUTTON}")
        except Exception as e:
            print(f"[FAIL] Process button NOT found: {PROCESS_MENU_BUTTON}")
            print(f"    Error: {e}")

        # ========== NAVIGATION STEPS ==========

        # Step 10: Click Process button
        print("\n[7] Clicking Process button...")
        try:
            await page.click(PROCESS_MENU_BUTTON, timeout=15000)
            print("[OK] Clicked Process button")
            await asyncio.sleep(2)
            screenshot_path = os.path.join(screenshot_dir, "nav_step1_process.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[OK] Screenshot: {screenshot_path}")
        except Exception as e:
            print(f"[FAIL] Could not click Process button: {e}")

        # Step 11: Look for and click Hire/Rehire link
        print("\n[8] Looking for Hire/Rehire link...")
        try:
            hire_link = await page.wait_for_selector(HIRE_REHIRE_LINK, timeout=15000)
            if hire_link:
                print(f"[OK] Hire/Rehire link FOUND: {HIRE_REHIRE_LINK}")
                await page.click(HIRE_REHIRE_LINK)
                print("[OK] Clicked Hire/Rehire link")
                await asyncio.sleep(2)
                screenshot_path = os.path.join(screenshot_dir, "nav_step2_hire_rehire.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[OK] Screenshot: {screenshot_path}")
            else:
                print(f"[FAIL] Hire/Rehire link NOT found")
        except Exception as e:
            print(f"[FAIL] Hire/Rehire link NOT found: {e}")

        # Step 12: Look for and click Go to Hire button
        print("\n[9] Looking for Go to Hire button...")
        try:
            hire_button = await page.wait_for_selector(GO_TO_HIRE_BUTTON, timeout=15000)
            if hire_button:
                print(f"[OK] Go to Hire button FOUND: {GO_TO_HIRE_BUTTON}")
                await page.click(GO_TO_HIRE_BUTTON)
                print("[OK] Clicked Go to Hire button")
                await asyncio.sleep(2)
                screenshot_path = os.path.join(screenshot_dir, "nav_step3_go_to_hire.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[OK] Screenshot: {screenshot_path}")
            else:
                print(f"[FAIL] Go to Hire button NOT found")
        except Exception as e:
            print(f"[FAIL] Go to Hire button NOT found: {e}")

        # Step 13: Look for and click HR PR New Hires card
        print("\n[10] Looking for HR PR New Hires card...")
        try:
            new_hire_card = await page.wait_for_selector(HR_PR_NEW_HIRES_CARD, timeout=15000)
            if new_hire_card:
                print(f"[OK] HR PR New Hires card FOUND: {HR_PR_NEW_HIRES_CARD}")
                await page.click(HR_PR_NEW_HIRES_CARD)
                print("[OK] Clicked HR PR New Hires card")
                await asyncio.sleep(3)
                screenshot_path = os.path.join(screenshot_dir, "nav_step4_new_hire_card.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[OK] Screenshot: {screenshot_path}")

                # Final screenshot of the new hire form
                await asyncio.sleep(2)
                screenshot_path = os.path.join(screenshot_dir, "new_hire_form.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[OK] Final form screenshot: {screenshot_path}")
            else:
                print(f"[FAIL] HR PR New Hires card NOT found")
        except Exception as e:
            print(f"[FAIL] HR PR New Hires card NOT found: {e}")

        # ========== FORM FIELD FILLING TEST ==========

        # Step 14: Test filling first name and last name fields
        print("\n[11] Testing form field filling...")
        print("    (Filling ONLY first name and last name for verification)")

        try:
            # Fill first name
            print(f"\n[12] Filling first name field: {FIRST_NAME_INPUT}")
            await page.wait_for_selector(FIRST_NAME_INPUT, timeout=10000)
            await page.fill(FIRST_NAME_INPUT, "Test")
            print("[OK] First name filled with 'Test'")

            # Fill last name
            print(f"\n[13] Filling last name field: {LAST_NAME_INPUT}")
            await page.wait_for_selector(LAST_NAME_INPUT, timeout=10000)
            await page.fill(LAST_NAME_INPUT, "Navigation")
            print("[OK] Last name filled with 'Navigation'")

            # Take screenshot of filled fields
            await asyncio.sleep(1)
            screenshot_path = os.path.join(screenshot_dir, "form_fields_filled.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[OK] Screenshot of filled fields: {screenshot_path}")

        except Exception as e:
            print(f"[FAIL] Form field filling failed: {e}")
            import traceback
            traceback.print_exc()

        # Step 15: Wait for manual inspection (reduced to 30 seconds)
        print("\n[14] Waiting 30 seconds for manual inspection...")
        print("    (You can inspect the filled form now)")
        print("    WARNING: Browser will close WITHOUT saving the form")
        for i in range(30, 0, -10):
            print(f"    Closing in {i} seconds...")
            await asyncio.sleep(10)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close browser
        if browser:
            print("\n[15] Closing browser WITHOUT saving...")
            await browser.close()
            print("[OK] Browser closed (form was NOT saved)")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
