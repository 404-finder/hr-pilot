"""
New hire form automation.

Fills out and submits the ADP new hire form with validated data.
"""

import logging

from playwright.async_api import Page

from src.adp.base_form import click_and_wait, click_visible_next_button, fill_date_field, fill_mdf_dropdown, fill_text_field
from src.adp.exceptions import FormSubmissionError
from src.config_tables import (
    JOB_TITLES,
    REASON_FOR_HIRE,
    TAX_ID_TYPE,
    WORK_SCHEDULE,
    get_everify_location,
    get_home_department,
    get_manager,
    get_search_code,
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
    EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT_ALT,
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
    VALIDATION_POPUP_GO_TO_NEXT_ALT,
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
    warnings: list[str] = []

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

        # Wait for the form to become fully interactive after navigation.
        # VPS latency means fields can be visible but not yet interactive.
        await page.wait_for_timeout(5000)

        # Diagnostic screenshot to see form state before first fill attempt
        await page.screenshot(path="screenshots/form_pre_fill_debug.png", timeout=60000)
        logger.info(f"Pre-fill screenshot saved. URL: {page.url}")

        # Fill basic information — first field gets longer timeout because ADP
        # can re-render the form DOM after initial visibility (especially post-MFA).
        await fill_text_field(page, FIRST_NAME_INPUT, hire.first_name, timeout=30000)
        await fill_text_field(page, LAST_NAME_INPUT, hire.last_name)
        await fill_text_field(page, PHONE_INPUT, hire.phone)
        await fill_text_field(page, PERSONAL_EMAIL_INPUT, hire.email)

        # Check "Use for Notification" checkbox
        # Element may be behind overlay or outside viewport — use JS evaluate to bypass
        logger.info("Checking 'Use for Notification' checkbox")
        await page.wait_for_selector(USE_FOR_NOTIFICATION_CHECKBOX, timeout=20000)
        checked = False
        try:
            await page.locator(USE_FOR_NOTIFICATION_CHECKBOX).evaluate("el => el.click()")
            checked = await page.is_checked(USE_FOR_NOTIFICATION_CHECKBOX)
        except Exception as e:
            logger.warning(f"locator.evaluate click failed for notification checkbox: {e}")
        if checked:
            logger.info("CONFIRMED: 'Use for Notification' checkbox is checked")
        else:
            logger.warning("WARNING: 'Use for Notification' checkbox may not be checked")

        # Fill hire date
        hire_date_str = hire.start_date.strftime("%m/%d/%Y")
        await fill_date_field(page, HIRE_DATE_INPUT, hire_date_str)

        # Select reason for hire (resolve from config_tables)
        reason_label = REASON_FOR_HIRE[hire.reason]
        reason_match = reason_label.split(" - ", 1)[1].strip() if " - " in reason_label else reason_label
        await fill_mdf_dropdown(page, REASON_FOR_HIRE_SELECT, get_search_code(reason_label), reason_match)
        logger.debug(f"Selected reason for hire: {reason_label}")

        # Select company code (from store config)
        company_code = store_config["company_code"]
        await fill_mdf_dropdown(page, COMPANY_CODE_SELECT, get_search_code(company_code), company_code)
        logger.debug(f"Selected company code: {company_code}")

        # Company code selection can trigger ADP to re-render dependent fields
        await page.wait_for_timeout(2000)

        # Select tax ID type (always SSN)
        await fill_mdf_dropdown(page, TAX_ID_TYPE_SELECT, "United", "Social Security", timeout=20000)
        logger.debug("Selected tax ID type: SSN")

        # Wait for Associate ID to generate
        logger.debug("Waiting 2 seconds for Associate ID to generate...")
        await page.wait_for_timeout(2000)

        # Capture Associate ID
        await page.wait_for_selector(ASSOCIATE_ID_INPUT, timeout=20000)
        associate_id = await page.input_value(ASSOCIATE_ID_INPUT)
        logger.info(f"Captured Associate ID: {associate_id}")

        # ====================================================================
        # ASK THE NEW HIRE MODAL
        # ====================================================================
        logger.info("Opening 'Ask the New Hire' modal")

        # Wait for ADP's loading spinner to disappear before proceeding.
        # Company Code / Tax ID Type selections trigger async re-renders.
        try:
            spinner = page.locator(".sdf-spinner, .vdl-spinner, [class*='spinner'], [class*='loading']").first
            await spinner.wait_for(state="hidden", timeout=15000)
            logger.info("Loading spinner disappeared")
        except Exception:
            logger.info("No spinner detected or already gone")

        await page.wait_for_selector(ASK_NEW_HIRE_BUTTON, timeout=20000)
        await page.click(ASK_NEW_HIRE_BUTTON)
        await page.wait_for_timeout(3000)  # Wait for modal to fully render

        # Debug: capture modal state to identify correct selectors
        await page.screenshot(path="screenshots/modal_debug.png", timeout=60000)
        logger.info("Modal debug screenshot saved to screenshots/modal_debug.png")

        # Debug: probe for onboarding experience element with alternative selectors
        alt_selectors = {
            "original #assignedTemplateName_Id": '#assignedTemplateName_Id',
            "[id*='assignedTemplate']": '[id*="assignedTemplate"]',
            "[id*='onboarding']": '[id*="onboarding"]',
            "[id*='Onboarding']": '[id*="Onboarding"]',
            "[id*='template']": '[id*="template"]',
            "[id*='Template']": '[id*="Template"]',
            "text='Assign onboarding experience'": 'text=Assign onboarding experience',
        }
        for label, sel in alt_selectors.items():
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    el = page.locator(sel).first
                    tag = await el.evaluate("el => el.tagName")
                    el_id = await el.evaluate("el => el.id || '(no id)'")
                    outer = await el.evaluate("el => el.outerHTML.substring(0, 200)")
                    logger.info(f"FOUND [{label}]: count={count}, tag={tag}, id={el_id}, html={outer}")
                else:
                    logger.info(f"NOT FOUND [{label}]")
            except Exception as e:
                logger.info(f"ERROR [{label}]: {e}")

        # Debug: look for pencil/edit icon or button near "onboarding" text
        try:
            role_btn = page.get_by_role("button", name="Assign onboarding experience")
            role_count = await role_btn.count()
            if role_count > 0:
                outer = await role_btn.first.evaluate("el => el.outerHTML.substring(0, 200)")
                logger.info(f"FOUND [role=button 'Assign onboarding experience']: count={role_count}, html={outer}")
            else:
                logger.info("NOT FOUND [role=button 'Assign onboarding experience']")
        except Exception as e:
            logger.info(f"ERROR [role=button 'Assign onboarding experience']: {e}")

        # Debug: dump all clickable elements inside the modal
        try:
            modal_html = await page.evaluate("""() => {
                const modal = document.querySelector('[role="dialog"], .modal, [class*="modal"], [class*="Modal"], [class*="slider"], [class*="Slider"]');
                if (modal) return modal.innerHTML.substring(0, 3000);
                return '(no modal container found)';
            }""")
            logger.info(f"Modal inner HTML (first 3000 chars): {modal_html}")
        except Exception as e:
            logger.info(f"ERROR dumping modal HTML: {e}")

        # Assign Onboarding Experience sub-flow (from store config)
        onboarding_experience = store_config["onboarding_experience"]
        logger.info(f"Assigning onboarding experience: {onboarding_experience}")
        await page.wait_for_selector(ASSIGN_ONBOARDING_BUTTON, timeout=20000)
        await page.click(ASSIGN_ONBOARDING_BUTTON)
        await fill_mdf_dropdown(page, ONBOARDING_TEMPLATE_SELECT, get_search_code(onboarding_experience), onboarding_experience)
        await page.click(ASSIGN_EXP_BUTTON)
        await page.click(BACK_BUTTON)
        logger.debug(f"Assigned onboarding experience: {onboarding_experience}")

        # Select Worked In State (from store config)
        worked_in_state = store_config["worked_in_state"]
        logger.info(f"Selecting worked in state: {worked_in_state}")
        await fill_mdf_dropdown(page, WORKED_IN_STATE_SELECT, get_search_code(worked_in_state), worked_in_state.split(" - ", 1)[1])
        logger.debug(f"Selected worked in state: {worked_in_state}")

        # Reports To (Manager) sub-flow (auto-derived from store number)
        manager = get_manager(hire.store_number)
        logger.info(f"Assigning manager: {manager['name']}")
        await page.wait_for_selector(REPORTS_TO_BUTTON, timeout=20000)
        await page.click(REPORTS_TO_BUTTON)
        await page.wait_for_timeout(3000)  # Wait for Reports To slider animation
        await page.wait_for_selector(MANAGER_NAME_SEARCH_INPUT, timeout=20000)

        manager_selected = False
        search_terms = [manager["search"], manager["name"]]
        for search_term in search_terms:
            logger.info(f"Searching manager with: '{search_term}'")
            await page.fill(MANAGER_NAME_SEARCH_INPUT, "")
            await page.fill(MANAGER_NAME_SEARCH_INPUT, search_term)
            await page.click(MANAGER_SEARCH_BUTTON)
            await page.wait_for_timeout(3000)

            # Only fall back if "There are no entries" is actually present
            no_entries = await page.evaluate(
                "document.body.innerText.includes('There are no entries')"
            )
            if no_entries:
                logger.warning(f"Manager search no entries for '{search_term}', trying next term")
                continue

            # Click the first unchecked radio button in the results
            logger.info("Clicking first radio button in results")
            await page.wait_for_selector(
                'sdf-radio-button[role="radio"][aria-checked="false"]', timeout=20000
            )
            await page.click('sdf-radio-button[role="radio"][aria-checked="false"]')

            # Verify selection took effect
            await page.wait_for_timeout(500)
            checked = await page.query_selector(
                'sdf-radio-button[role="radio"][aria-checked="true"]'
            )
            if checked:
                manager_selected = True
                logger.info(f"Manager radio button confirmed selected for '{search_term}'")
                break
            else:
                logger.warning(f"Radio button click did not register for '{search_term}', trying next term")

        if not manager_selected:
            warn_msg = f"Manager search failed for '{manager['name']}' — skipping manager assignment"
            logger.warning(warn_msg)
            warnings.append(warn_msg)
            # Dismiss the Reports To slider so it doesn't block subsequent fields
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        else:
            await page.click(SAVE_MANAGER_BUTTON)
            logger.debug(f"Assigned manager: {manager['name']}")

        # Select E-Verify Work Location (from store number)
        everify_location = get_everify_location(hire.store_number)
        logger.info(f"Selecting E-Verify work location: {everify_location}")
        await fill_mdf_dropdown(page, E_VERIFY_LOCATION_SELECT, everify_location, everify_location)
        logger.debug(f"Selected E-Verify location: {everify_location}")

        # Save modal
        logger.info("Saving 'Ask the New Hire' modal")
        await page.wait_for_selector(SAVE_MODAL_BUTTON, timeout=20000)
        await page.click(SAVE_MODAL_BUTTON)

        # Debug screenshot after personal section
        await capture_screenshot(page, "debug_personal_done")

        # ====================================================================
        # PROCEED TO EMPLOYMENT SECTION
        # ====================================================================
        logger.info("Proceeding to Employment section")

        await page.wait_for_selector(NEXT_BUTTON_PRIMARY, timeout=20000)
        await page.click(NEXT_BUTTON_PRIMARY)

        # Handle validation popup — "Go to Next Section" button.
        # ADP shows this when optional fields (SSN, DOB, address) are empty.
        # Try multiple selectors: sdf-button aria-label, text-based, then role-based.
        popup_locator = page.locator(
            VALIDATION_POPUP_GO_TO_NEXT
        ).or_(page.locator(
            VALIDATION_POPUP_GO_TO_NEXT_ALT
        )).or_(page.get_by_role(
            "button", name="Go to Next Section"
        ))
        try:
            await popup_locator.wait_for(timeout=20000)
            await popup_locator.click()
            logger.info("Clicked validation popup 'Go to Next Section' (Personal)")
        except Exception:
            logger.debug("No validation popup appeared after Personal section")

        await page.wait_for_timeout(3000)  # Wait for Employment section to become visible

        # ====================================================================
        # EMPLOYMENT SECTION
        # ====================================================================
        logger.info("Filling employment section")

        # Job Title (resolve from config_tables)
        job_title_label = JOB_TITLES[hire.job_title]
        job_title_match = job_title_label.split(" - ", 1)[1].strip() if " - " in job_title_label else job_title_label
        logger.info(f"Filling Job Title with value: {job_title_label}")
        await fill_mdf_dropdown(page, JOB_TITLE_SELECT, get_search_code(job_title_label), job_title_match)
        job_title_el = await page.query_selector(f'[class*="MDFSelectBox__single-value"]:has-text("{job_title_match}")')
        if job_title_el:
            logger.info(f"CONFIRMED: Job Title = '{job_title_match}'")
        else:
            logger.warning(f"WARNING: Job Title may not have filled correctly (expected '{job_title_match}')")

        # Worker Category (resolve from config_tables)
        worker_category_label = WORK_SCHEDULE[hire.work_schedule]
        worker_category_match = worker_category_label.split(" - ", 1)[1].strip() if " - " in worker_category_label else worker_category_label
        logger.info(f"Filling Worker Category with value: {worker_category_label}")
        await fill_mdf_dropdown(page, WORKER_CATEGORY_SELECT, get_search_code(worker_category_label), worker_category_match)
        worker_cat_el = await page.query_selector(f'[class*="MDFSelectBox__single-value"]:has-text("{worker_category_match}")')
        if worker_cat_el:
            logger.info(f"CONFIRMED: Worker Category = '{worker_category_match}'")
        else:
            logger.warning(f"WARNING: Worker Category may not have filled correctly (expected '{worker_category_match}')")

        # Benefits Eligibility Class (from store config)
        benefits_eligibility = store_config["benefits_eligibility"]
        logger.info(f"Filling Benefits Eligibility Class with value: {benefits_eligibility}")
        await fill_mdf_dropdown(page, BENEFITS_ELIGIBILITY_CLASS_SELECT, "BE", "Benefit Eligible")
        benefits_el = await page.query_selector('[class*="MDFSelectBox__single-value"]:has-text("Benefit Eligible")')
        if benefits_el:
            logger.info("CONFIRMED: Benefits Eligibility Class = 'Benefit Eligible'")
        else:
            logger.warning("WARNING: Benefits Eligibility Class may not have filled correctly")

        # Calculate Using Measurement Periods radio (from store config)
        if store_config["measurement_periods"]:
            await page.wait_for_selector(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO, timeout=20000)
            await page.click(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO)
            logger.debug("Selected measurement periods option")

        # Home Department (auto-derived from store number + job title)
        home_department = get_home_department(hire.store_number, hire.job_title)
        logger.info(f"Filling Home Department with value: {home_department}")
        await fill_mdf_dropdown(page, HOME_DEPARTMENT_SELECT, home_department, home_department)
        home_dept_el = await page.query_selector(f'[class*="MDFSelectBox__single-value"]:has-text("{home_department}")')
        if home_dept_el:
            logger.info(f"CONFIRMED: Home Department = '{home_department}'")
        else:
            logger.warning(f"WARNING: Home Department may not have filled correctly (expected '{home_department}')")

        # Debug screenshot after employment section
        await capture_screenshot(page, "debug_employment_done")

        # Proceed to Payroll section
        logger.info("Proceeding to Payroll section")
        await click_visible_next_button(page, timeout=20000)
        await page.wait_for_timeout(3000)  # Wait for Payroll section to become visible

        # Handle validation popup — same pattern as Personal section.
        emp_popup_locator = page.locator(
            EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT
        ).or_(page.locator(
            EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT_ALT
        )).or_(page.get_by_role(
            "button", name="Go to Next Section"
        ))
        try:
            await emp_popup_locator.wait_for(timeout=20000)
            await emp_popup_locator.click()
            logger.info("Clicked validation popup 'Go to Next Section' (Employment)")
        except Exception:
            logger.debug("No validation popup appeared after Employment section")

        # ====================================================================
        # PAYROLL SECTION
        # ====================================================================
        logger.info("Filling payroll section")

        # Compensation Type (always Hourly)
        logger.info("Filling Compensation Type with value: Hourly")
        await fill_mdf_dropdown(page, COMPENSATION_TYPE_SELECT, "Hour", "Hourly")
        comp_el = await page.query_selector('[class*="MDFSelectBox__single-value"]:has-text("Hourly")')
        if comp_el:
            logger.info("CONFIRMED: Compensation Type = 'Hourly'")
        else:
            logger.warning("WARNING: Compensation Type may not have filled correctly")

        # Regular Pay Rate — use click+triple-click+type to trigger React onChange
        logger.info(f"Filling Regular Pay Rate with value: {hire.pay_rate}")
        await page.wait_for_selector(REGULAR_PAY_RATE_INPUT, timeout=20000)
        await page.click(REGULAR_PAY_RATE_INPUT)
        await page.keyboard.press("Control+a")
        await page.type(REGULAR_PAY_RATE_INPUT, str(hire.pay_rate))
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(500)
        actual_pay_rate = await page.input_value(REGULAR_PAY_RATE_INPUT)
        if actual_pay_rate:
            logger.info(f"CONFIRMED: Regular Pay Rate = '{actual_pay_rate}'")
        else:
            logger.warning(f"WARNING: Regular Pay Rate may not have filled correctly (expected '{hire.pay_rate}')")

        # Debug screenshot after payroll section
        await capture_screenshot(page, "debug_payroll_done")

        # Proceed to Tax section
        logger.info("Proceeding to Tax section")
        await click_visible_next_button(page, timeout=20000)
        await page.wait_for_timeout(3000)  # Wait for Tax section to become visible

        # ====================================================================
        # TAX SECTION
        # ====================================================================
        logger.info("Filling tax section")

        # SUI/SDI Tax Code (from store config)
        # Use worked_in_state ("TX - Texas" / "CO - Colorado") to derive search code and state name
        # as sui_sdi_tax_code has inconsistent formatting ("TX -53 -Texas" / "CO -15 - Colorado")
        sui_sdi_tax_code = store_config["sui_sdi_tax_code"]
        state_name = worked_in_state.split(" - ", 1)[1]
        await fill_mdf_dropdown(page, SUI_SDI_TAX_CODE_SELECT, get_search_code(worked_in_state), state_name)
        logger.debug(f"Selected SUI/SDI tax code: {sui_sdi_tax_code}")

        # Proceed to Direct Deposit section
        logger.info("Proceeding to Direct Deposit section (will skip)")
        await page.wait_for_selector(TAX_NEXT_BUTTON, timeout=20000)
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

        await click_visible_next_button(page, timeout=20000)

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
                "submitted": False,
                "warnings": warnings,
            }

        # ====================================================================
        # SAVE AND EXIT (only if dry_run=False)
        # ====================================================================
        logger.info("Submitting and saving new hire form")

        await page.wait_for_selector(SAVE_AND_EXIT_BUTTON, timeout=20000)
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
            "submitted": True,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(f"Failed to fill new hire form: {e}")
        screenshot_path = await capture_screenshot(page, "new_hire_error")
        raise FormSubmissionError(f"Failed to fill new hire form: {e}", screenshot_path)
