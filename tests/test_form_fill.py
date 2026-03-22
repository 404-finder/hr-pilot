"""
Full form fill test with dry-run mode.

Tests the complete new hire form filling workflow with test data.
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


async def main():
    """Test full form filling with dry-run mode."""
    print("=" * 80)
    print("FULL FORM FILL TEST - DRY RUN MODE")
    print("=" * 80)

    # Override headless setting for this test
    original_headless = settings.headless
    settings.headless = False
    print(f"\n[INFO] Running with headless=False (browser will be visible)")

    browser = None

    try:
        # Step 1: Create test NewHire object
        print("\n[1] Creating test NewHire object...")
        hire = NewHire(
            first_name="Test",
            last_name="FormFill",
            email="testformfill@fakeemail.com",
            phone="555-000-1234",
            store_number="39104",
            job_title="crew",
            work_schedule="part time",
            pay_rate=12.00,
            pay_frequency="hourly",
            start_date=date(2026, 3, 15),
            reason="new hire"
        )
        print("[OK] NewHire object created:")
        print(f"     Name: {hire.first_name} {hire.last_name}")
        print(f"     Email: {hire.email}")
        print(f"     Phone: {hire.phone}")
        print(f"     Store: {hire.store_number}")
        print(f"     Job: {hire.job_title} ({hire.work_schedule})")
        print(f"     Pay: ${hire.pay_rate}/hour")
        print(f"     Start Date: {hire.start_date}")
        print(f"     Reason: {hire.reason}")

        # Step 2: Login to ADP
        print("\n[2] Logging into ADP...")
        creds = settings.get_adp_credentials(settings.allowed_user_ids[0])
        browser, page, mfa_required = await login_to_adp(
            username=creds.username,
            password=creds.password.get_secret_value(),
        )
        if mfa_required:
            print("[FAIL] MFA required - cannot proceed in automated test")
            return
        print("[OK] Login successful!")

        # Step 3: Navigate to new hire form
        print("\n[3] Navigating to new hire form...")
        await navigate_to_new_hire(page)
        print("[OK] Navigation complete!")

        # Step 4: Fill form in dry-run mode
        print("\n[4] Filling form with dry_run=True...")
        print("    (This will fill all form sections but NOT submit)")
        result = await fill_new_hire_form(page, hire, dry_run=True)

        # Step 5: Print results
        print("\n[OK] Form filling complete!")
        print("=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(f"  Associate ID: {result['associate_id']}")
        print(f"  Screenshot Path: {result['screenshot_path']}")
        print(f"  Submitted: {result['submitted']}")
        print("=" * 80)

        # Step 6: Verify screenshot exists
        if os.path.exists(result['screenshot_path']):
            print(f"\n[OK] Screenshot saved successfully")
            print(f"     Location: {result['screenshot_path']}")
        else:
            print(f"\n[WARNING] Screenshot file not found at: {result['screenshot_path']}")

        # Step 7: Verify dry_run worked (submitted should be False)
        if result['submitted'] is False:
            print("\n[OK] Dry run mode worked correctly (form was NOT submitted)")
        else:
            print("\n[WARNING] Expected submitted=False but got True")

        # Step 8: Wait for manual inspection
        print("\n[5] Waiting 60 seconds for manual inspection...")
        print("    You can now inspect:")
        print("    - The browser window (form should be filled)")
        print("    - The screenshot file")
        print("    - The captured Associate ID")
        print("\n    NOTE: Form will NOT be saved (dry_run=True)")

        for i in range(60, 0, -10):
            print(f"    Closing in {i} seconds...")
            await asyncio.sleep(10)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Step 9: Close browser
        if browser:
            print("\n[6] Closing browser WITHOUT saving...")
            await browser.close()
            print("[OK] Browser closed (form was NOT saved)")

        # Restore original headless setting
        settings.headless = original_headless

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nSummary:")
    print("- Form was filled with test data")
    print("- Screenshot was captured for review")
    print("- Form was NOT submitted (dry_run=True)")
    print("- Browser was closed without saving")
    print("\nNext steps:")
    print("1. Review the screenshot in the screenshots/ directory")
    print("2. Verify all fields were filled correctly")
    print("3. If successful, the dry-run feature is working!")


if __name__ == "__main__":
    asyncio.run(main())
