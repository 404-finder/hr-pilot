"""
Live submit test — creates a REAL new hire record in ADP.

Fills the new hire form with dry_run=False to perform a real submission.
Does NOT send a registration code (PRC skipped).
"""

import asyncio
import os
import sys
from datetime import date

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adp.auth import login_to_adp
from src.adp.navigation import navigate_to_new_hire
from src.adp.new_hire_form import fill_new_hire_form
from src.config import settings
from src.models.new_hire import NewHire


async def dismiss_in_progress_popup(page) -> bool:
    """Dismiss the 'Did you start this hire already?' popup if it appears.

    Args:
        page: Active Playwright page.

    Returns:
        True if popup was found and dismissed, False if not present.
    """
    try:
        await page.wait_for_selector(
            'sdf-focus-pane[id="showInProgressActiveEmpInfo_Id"]',
            timeout=5000
        )
        print("[INFO] 'Did you start this hire already?' popup detected -- dismissing...")
        await page.click('sdf-button[aria-label="Yes"]')
        await page.wait_for_timeout(2000)
        print("[OK] In-progress popup dismissed")
        return True
    except Exception:
        print("[INFO] No in-progress popup detected -- continuing normally")
        return False


async def main():
    """Live submit test -- fills and submits a real new hire record in ADP."""
    print("=" * 80)
    print("LIVE SUBMIT TEST - dry_run=False")
    print("=" * 80)

    # Confirmation prompt before proceeding
    print("\nWARNING: This will create a real new hire record in ADP.")
    input("Press Enter to continue or Ctrl+C to abort...")

    # Override headless setting for this test
    original_headless = settings.headless
    settings.headless = False
    print("\n[INFO] Running with headless=False (browser will be visible)")

    browser = None

    try:
        # Step 1: Create test NewHire object
        print("\n[1] Creating test NewHire object...")
        hire = NewHire(
            first_name="Test",
            last_name="LiveSubmit",
            email="charles.annex830@slmails.com",
            phone="555-000-5678",
            store_number="39104",
            job_title="crew",
            work_schedule="part time",
            pay_rate=12.00,
            pay_frequency="hourly",
            start_date=date(2026, 3, 15),
            reason="new hire"
        )
        print("[OK] NewHire object created:")
        print(f"     Name:       {hire.first_name} {hire.last_name}")
        print(f"     Email:      {hire.email}")
        print(f"     Phone:      {hire.phone}")
        print(f"     Store:      {hire.store_number}")
        print(f"     Job:        {hire.job_title} ({hire.work_schedule})")
        print(f"     Pay:        ${hire.pay_rate}/hour")
        print(f"     Start Date: {hire.start_date}")
        print(f"     Reason:     {hire.reason}")

        # Step 2: Login to ADP
        print("\n[2] Logging into ADP...")
        browser, page = await login_to_adp()
        print("[OK] Login successful!")

        # Step 3: Navigate to new hire form
        print("\n[3] Navigating to new hire form...")
        await navigate_to_new_hire(page)
        print("[OK] Navigation complete!")

        # Step 4: Handle "Did you start this hire already?" popup
        print("\n[4] Checking for in-progress hire popup...")
        await dismiss_in_progress_popup(page)

        # Step 5: Fill and submit form with dry_run=False
        print("\n[5] Filling and submitting form with dry_run=False...")
        print("    (This WILL submit -- a real record will be created in ADP)")
        result = await fill_new_hire_form(page, hire, dry_run=False)

        # Step 6: Print result
        print("\n[OK] Form submitted successfully!")
        print("=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(f"  associate_id:    {result['associate_id']}")
        print(f"  screenshot_path: {result['screenshot_path']}")
        print(f"  submitted:       {result['submitted']}")
        print(f"  warnings:        {result['warnings']}")
        print("=" * 80)

        # Step 7: Wait 30 seconds to allow manual verification in ADP
        print("\n[6] Waiting 30 seconds -- verify record in ADP In-Progress Hires list...")
        for remaining in range(30, 0, -5):
            print(f"    Closing browser in {remaining} seconds...")
            await asyncio.sleep(5)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Step 8: Close browser (no PRC sent)
        if browser:
            print("\n[7] Closing browser (PRC skipped as requested)...")
            await browser.close()
            print("[OK] Browser closed")

        # Restore original headless setting
        settings.headless = original_headless

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
