"""
New hire form automation.

Fills out and submits the ADP new hire form with validated data.
"""

import logging

from playwright.async_api import Page

from src.adp.base_form import click_and_wait, fill_date_field, fill_text_field, fill_react_dropdown
from src.adp.exceptions import FormSubmissionError
from src.config_tables import (
    JOB_TITLES,
    REASON_FOR_HIRE,
    TAX_ID_TYPE,
    WORK_SCHEDULE,
    get_everify_location,
    get_home_department,
    get_manager,
    get_store_config,
)
from src.adp.selectors.new_hire import (
    ASSIGN_EXP_BUTTON,
    ASSIGN_ONBOARDING_BUTTON,
    ASK_NEW_HIRE_BUTTON,
    ASSOCIATE_ID_INPUT,
    BACK_BUTTON,
    BENEFITS_ELIGIBILITY_CLASS_SELECT,
    CALCULATE_USING_MEASUREMENT_PERIODS_RADIO,
    COMPANY_CODE_SELECT,
    COMPENSATION_TYPE_SELECT,
    EMERGENCY_CONTACT_NEXT_BUTTON,
    EMPLOYMENT_NEXT_BUTTON,
    EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT,
    E_VERIFY_LOCATION_SELECT,
    FIRST_NAME_INPUT,
    HIRE_DATE_INPUT,
    HOME_DEPARTMENT_SELECT,
    JOB_TITLE_SELECT,
    LAST_NAME_INPUT,
    MANAGER_NAME_SEARCH_INPUT,
    MANAGER_RADIO_BUTTON,
    MANAGER_SEARCH_BUTTON,
    NEXT_BUTTON_PRIMARY,
    ONBOARDING_TEMPLATE_SELECT,
    PAYROLL_NEXT_BUTTON,
    PERSONAL_EMAIL_INPUT,
    PHONE_INPUT,
    REASON_FOR_HIRE_SELECT,
    REGULAR_PAY_RATE_INPUT,
    REPORTS_TO_BUTTON,
    SAVE_AND_EXIT_BUTTON,
    SAVE_MANAGER_BUTTON,
    SAVE_MODAL_BUTTON,
    SUI_SDI_TAX_CODE_SELECT,
    TAX_ID_TYPE_SELECT,
    TAX_NEXT_BUTTON,
    USE_FOR_NOTIFICATION_CHECKBOX,
    VALIDATION_POPUP_GO_TO_NEXT,
    WORKER_CATEGORY_SELECT,
    WORKED_IN_STATE_SELECT,
)
from src.models.new_hire import NewHire
from src.utils.screenshots import capture_screenshot

logger = logging.getLogger(__name__)


async def fill_new_hire_form(page: Page, hire: NewHire, dry_run: bool = True) -> dict:
    """Fill out the ADP new hire form with dry run support.

    Args:
        page: Authenticated ADP page (already navigated to new hire form).
        hire: Validated new hire data.
        dry_run: If True, fills form but doesn't submit. If False, submits the form.

    Returns:
        Dictionary with:
            - associate_id (str): The captured Associate ID
            - screenshot_path (str): Path to the screenshot
            - submitted (bool): Whether the form was actually submitted

    Raises:
        FormSubmissionError: If form submission fails.
    """
    try:
        logger.info(f"Starting new hire form for {hire.first_name} {hire.last_name}")

        # Get store configuration
        store_config = get_store_config(hire.store_number)
        if not store_config:
            raise FormSubmissionError(f"No configuration found for store {hire.store_number}")

        logger.info(f"Using store config for {hire.store_number}: {store_config}")

        # ====================================================================
        # PERSONAL SECTION
        # ====================================================================
        logger.info("Filling personal information section")

        # Fill basic information
        await fill_text_field(page, FIRST_NAME_INPUT, hire.first_name)
        await fill_text_field(page, LAST_NAME_INPUT, hire.last_name)
        await fill_text_field(page, PHONE_INPUT, hire.phone)
        await fill_text_field(page, PERSONAL_EMAIL_INPUT, hire.email)

        # Check "Use for Notification" checkbox
        # Use JavaScript to check the checkbox directly (ADP forms have viewport issues)
        await page.wait_for_selector(USE_FOR_NOTIFICATION_CHECKBOX, timeout=10000)
        await page.evaluate(f'''
            document.querySelector('{USE_FOR_NOTIFICATION_CHECKBOX}').checked = true;
            document.querySelector('{USE_FOR_NOTIFICATION_CHECKBOX}').dispatchEvent(new Event('change', {{ bubbles: true }}));
        ''')
        logger.debug("Checked 'Use for Notification' checkbox using JavaScript")

        # Fill hire date
        hire_date_str = hire.start_date.strftime("%m/%d/%Y")
        await fill_date_field(page, HIRE_DATE_INPUT, hire_date_str)

        # Select reason for hire (resolve from config_tables)
        # This is a React Select dropdown
        reason_label = REASON_FOR_HIRE[hire.reason]
        await fill_react_dropdown(page, REASON_FOR_HIRE_SELECT, reason_label)
        logger.debug(f"Selected reason for hire: {reason_label}")

        # Select company code (from store config)
        # This is a React Select dropdown
        company_code = store_config["company_code"]
        await fill_react_dropdown(page, COMPANY_CODE_SELECT, company_code)
        logger.debug(f"Selected company code: {company_code}")

        # Select tax ID type (always SSN)
        # This is a React Select dropdown
        tax_id_label = TAX_ID_TYPE["ssn"]
        await fill_react_dropdown(page, TAX_ID_TYPE_SELECT, tax_id_label)
        logger.debug("Selected tax ID type: SSN")

        # Wait for Associate ID to generate
        logger.debug("Waiting 2 seconds for Associate ID to generate...")
        await page.wait_for_timeout(2000)

        # Capture Associate ID
        await page.wait_for_selector(ASSOCIATE_ID_INPUT, timeout=10000)
        associate_id = await page.input_value(ASSOCIATE_ID_INPUT)
        logger.info(f"Captured Associate ID: {associate_id}")

        # ====================================================================
        # ASK THE NEW HIRE MODAL
        # ====================================================================
        logger.info("Opening 'Ask the New Hire' modal")

        await page.wait_for_selector(ASK_NEW_HIRE_BUTTON, timeout=10000)
        await page.click(ASK_NEW_HIRE_BUTTON)

        # Assign Onboarding Experience sub-flow (from store config)
        onboarding_experience = store_config["onboarding_experience"]
        logger.info(f"Assigning onboarding experience: {onboarding_experience}")
        await page.wait_for_selector(ASSIGN_ONBOARDING_BUTTON, timeout=10000)
        await page.click(ASSIGN_ONBOARDING_BUTTON)
        # This is a React Select dropdown
        await fill_react_dropdown(page, ONBOARDING_TEMPLATE_SELECT, onboarding_experience)
        await page.click(ASSIGN_EXP_BUTTON)
        await page.click(BACK_BUTTON)
        logger.debug(f"Assigned onboarding experience: {onboarding_experience}")

        # Select Worked In State (from store config)
        # This is a React Select dropdown
        worked_in_state = store_config["worked_in_state"]
        logger.info(f"Selecting worked in state: {worked_in_state}")
        await fill_react_dropdown(page, WORKED_IN_STATE_SELECT, worked_in_state)
        logger.debug(f"Selected worked in state: {worked_in_state}")

        # Reports To (Manager) sub-flow (auto-derived from store number)
        manager_name = get_manager(hire.store_number)
        logger.info(f"Assigning manager: {manager_name}")
        await page.wait_for_selector(REPORTS_TO_BUTTON, timeout=10000)
        await page.click(REPORTS_TO_BUTTON)
        await page.wait_for_selector(MANAGER_NAME_SEARCH_INPUT, timeout=10000)
        await page.fill(MANAGER_NAME_SEARCH_INPUT, manager_name)
        await page.click(MANAGER_SEARCH_BUTTON)

        # Wait for search results to load
        await page.wait_for_timeout(3000)

        # Click the first radio button in the search results using JavaScript
        # The modal has multiple radio buttons, we want the first one in the results table
        await page.evaluate('''
            const radioButtons = document.querySelectorAll('#reportsToLabel_Id sdf-radio-button');
            if (radioButtons.length > 0) {
                radioButtons[0].click();
            }
        ''')
        await page.click(SAVE_MANAGER_BUTTON)
        logger.debug(f"Assigned manager: {manager_name}")

        # Select E-Verify Work Location (from store number)
        # This is a React Select dropdown
        everify_location = get_everify_location(hire.store_number)
        logger.info(f"Selecting E-Verify work location: {everify_location}")
        await fill_react_dropdown(page, E_VERIFY_LOCATION_SELECT, everify_location)
        logger.debug(f"Selected E-Verify location: {everify_location}")

        # Save modal
        logger.info("Saving 'Ask the New Hire' modal")
        await page.wait_for_selector(SAVE_MODAL_BUTTON, timeout=10000)
        await page.click(SAVE_MODAL_BUTTON)

        # ====================================================================
        # PROCEED TO EMPLOYMENT SECTION
        # ====================================================================
        logger.info("Proceeding to Employment section")

        await page.wait_for_selector(NEXT_BUTTON_PRIMARY, timeout=10000)
        await page.click(NEXT_BUTTON_PRIMARY)

        # Handle validation popup if it appears
        try:
            await page.wait_for_selector(VALIDATION_POPUP_GO_TO_NEXT, timeout=3000)
            await page.click(VALIDATION_POPUP_GO_TO_NEXT)
            logger.debug("Clicked through validation popup")
        except Exception:
            logger.debug("No validation popup appeared")

        # ====================================================================
        # EMPLOYMENT SECTION
        # ====================================================================
        logger.info("Filling employment section")

        # Job Title (resolve from config_tables)
        # This is a React Select dropdown
        job_title_label = JOB_TITLES[hire.job_title]
        await fill_react_dropdown(page, JOB_TITLE_SELECT, job_title_label)
        logger.debug(f"Selected job title: {job_title_label}")

        # Worker Category (resolve from config_tables)
        # This is a React Select dropdown
        worker_category_label = WORK_SCHEDULE[hire.work_schedule]
        await fill_react_dropdown(page, WORKER_CATEGORY_SELECT, worker_category_label)
        logger.debug(f"Selected worker category: {worker_category_label}")

        # Benefits Eligibility Class (from store config)
        # This is a React Select dropdown
        benefits_eligibility = store_config["benefits_eligibility"]
        await fill_react_dropdown(page, BENEFITS_ELIGIBILITY_CLASS_SELECT, benefits_eligibility)
        logger.debug(f"Selected benefits eligibility class: {benefits_eligibility}")

        # Calculate Using Measurement Periods radio (from store config)
        if store_config["measurement_periods"]:
            await page.wait_for_selector(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO, timeout=10000)
            await page.click(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO)
            logger.debug("Selected measurement periods option")

        # Home Department (auto-derived from store number + job title)
        # This is a React Select dropdown
        home_department = get_home_department(hire.store_number, hire.job_title)
        await fill_react_dropdown(page, HOME_DEPARTMENT_SELECT, home_department)
        logger.debug(f"Selected home department: {home_department}")

        # Proceed to Payroll section
        logger.info("Proceeding to Payroll section")
        await page.wait_for_selector(EMPLOYMENT_NEXT_BUTTON, timeout=10000)
        await page.click(EMPLOYMENT_NEXT_BUTTON)

        # Handle validation popup if it appears
        try:
            await page.wait_for_selector(EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT, timeout=3000)
            await page.click(EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT)
            logger.debug("Clicked through employment validation popup")
        except Exception:
            logger.debug("No validation popup appeared")

        # ====================================================================
        # PAYROLL SECTION
        # ====================================================================
        logger.info("Filling payroll section")

        # Compensation Type (always Hourly)
        # This is a React Select dropdown
        await fill_react_dropdown(page, COMPENSATION_TYPE_SELECT, "Hourly")
        logger.debug("Selected Hourly compensation type")

        # Regular Pay Rate
        await fill_text_field(page, REGULAR_PAY_RATE_INPUT, str(hire.pay_rate))
        logger.debug(f"Entered pay rate: {hire.pay_rate}")

        # Proceed to Tax section
        logger.info("Proceeding to Tax section")
        await page.wait_for_selector(PAYROLL_NEXT_BUTTON, timeout=10000)
        await page.click(PAYROLL_NEXT_BUTTON)

        # ====================================================================
        # TAX SECTION
        # ====================================================================
        logger.info("Filling tax section")

        # SUI/SDI Tax Code (from store config)
        # This is a React Select dropdown
        sui_sdi_tax_code = store_config["sui_sdi_tax_code"]
        await fill_react_dropdown(page, SUI_SDI_TAX_CODE_SELECT, sui_sdi_tax_code)
        logger.debug(f"Selected SUI/SDI tax code: {sui_sdi_tax_code}")

        # Proceed to Direct Deposit section
        logger.info("Proceeding to Direct Deposit section (will skip)")
        await page.wait_for_selector(TAX_NEXT_BUTTON, timeout=10000)
        await page.click(TAX_NEXT_BUTTON)

        # ====================================================================
        # DIRECT DEPOSIT SECTION (SKIP)
        # ====================================================================
        logger.info("Skipping Direct Deposit section")

        # Just click Next to skip
        # Note: The selector is 'button[name="ddNext"]' but we might be at emergency contact
        # Let's try to find the Next button generically
        await page.wait_for_timeout(2000)  # Brief wait for page load

        # ====================================================================
        # EMERGENCY CONTACT SECTION (SKIP)
        # ====================================================================
        logger.info("Skipping Emergency Contact section")

        await page.wait_for_selector(EMERGENCY_CONTACT_NEXT_BUTTON, timeout=10000)
        await page.click(EMERGENCY_CONTACT_NEXT_BUTTON)

        # ====================================================================
        # DRY RUN CHECK
        # ====================================================================
        # Take screenshot of filled form for review
        screenshot_filename = f"new_hire_review_{hire.first_name}_{hire.last_name}".replace(" ", "_")
        screenshot_path = await capture_screenshot(page, screenshot_filename)
        logger.info(f"Captured review screenshot: {screenshot_path}")

        if dry_run:
            # Dry run mode - DO NOT submit
            logger.info(f"Dry run mode - NOT submitting form for {hire.first_name} {hire.last_name}")
            logger.info(f"Associate ID: {associate_id}")
            return {
                "associate_id": associate_id,
                "screenshot_path": screenshot_path,
                "submitted": False
            }

        # ====================================================================
        # SAVE AND EXIT (only if dry_run=False)
        # ====================================================================
        logger.info("Submitting and saving new hire form")

        await page.wait_for_selector(SAVE_AND_EXIT_BUTTON, timeout=10000)
        await page.click(SAVE_AND_EXIT_BUTTON)

        # Wait for redirect to In-Progress Hires page
        await page.wait_for_timeout(3000)

        # Take success screenshot
        screenshot_filename = f"new_hire_submitted_{hire.first_name}_{hire.last_name}".replace(" ", "_")
        screenshot_path = await capture_screenshot(page, screenshot_filename)

        logger.info(f"Successfully submitted new hire: {hire.first_name} {hire.last_name}")
        logger.info(f"Associate ID: {associate_id}")

        return {
            "associate_id": associate_id,
            "screenshot_path": screenshot_path,
            "submitted": True
        }

    except Exception as e:
        logger.error(f"Failed to fill new hire form: {e}")
        screenshot_path = await capture_screenshot(page, "new_hire_error")
        raise FormSubmissionError(f"Failed to fill new hire form: {e}", screenshot_path)
