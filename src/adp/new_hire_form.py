"""
New hire form automation.

Fills out and submits the ADP new hire form with validated data.
"""

import logging

from playwright.async_api import Page

from src.adp.base_form import click_and_wait, click_visible_next_button, fill_date_field, fill_mdf_dropdown, fill_text_field, select_dropdown
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
    ASSIGN_ONBOARDING_BUTTON_ALT1,
    ASSIGN_ONBOARDING_BUTTON_ALT2,
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

        # Assign Onboarding Experience sub-flow (from store config)
        onboarding_experience = store_config["onboarding_experience"]
        logger.info(f"Assigning onboarding experience: {onboarding_experience}")

        # === DIAGNOSTIC: dump all clickable elements in the modal area ===
        await page.wait_for_timeout(3000)  # let modal fully render
        await capture_screenshot(page, "modal_pre_click_debug")

        modal_dump = await page.evaluate("""() => {
            const all = document.querySelectorAll('a, button, [role="button"], input, svg, [onclick]');
            const results = [];
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                const text = (el.textContent || '').trim().substring(0, 80);
                const id = el.id || '';
                const classes = el.className || '';
                const tag = el.tagName;
                const ariaLabel = el.getAttribute('aria-label') || '';
                if (text.toLowerCase().includes('assign') ||
                    text.toLowerCase().includes('onboard') ||
                    text.toLowerCase().includes('none') ||
                    text.toLowerCase().includes('pencil') ||
                    text.toLowerCase().includes('edit') ||
                    id.toLowerCase().includes('assign') ||
                    id.toLowerCase().includes('template') ||
                    id.toLowerCase().includes('onboard') ||
                    ariaLabel.toLowerCase().includes('assign') ||
                    ariaLabel.toLowerCase().includes('edit') ||
                    (rect.top > 100 && rect.top < 300 && rect.left > 400 && rect.left < 800)) {
                    results.push({
                        tag, id, classes: String(classes).substring(0, 100),
                        ariaLabel, text: text.substring(0, 80),
                        visible: rect.width > 0 && rect.height > 0,
                        rect: {top: Math.round(rect.top), left: Math.round(rect.left), w: Math.round(rect.width), h: Math.round(rect.height)}
                    });
                }
            }
            return JSON.stringify(results, null, 2);
        }""")
        logger.info(f"Modal clickable elements dump: {modal_dump}")
        # === END DIAGNOSTIC ===

        # Multi-strategy click: the onboarding edit button is an SDF custom
        # element that Playwright may not consider "visible" (zero-dimension
        # <a> tag or shadow DOM wrapper).
        onboarding_clicked = False

        # Strategy 1: Original selector with state="attached" + JS click
        try:
            el = page.locator(ASSIGN_ONBOARDING_BUTTON)
            await el.wait_for(state="attached", timeout=10000)
            await el.evaluate("el => el.click()")
            onboarding_clicked = True
            logger.info("Onboarding button clicked via strategy 1 (original ID + JS click)")
        except Exception as e:
            logger.warning(f"Strategy 1 failed ({ASSIGN_ONBOARDING_BUTTON}): {e}")

        # Strategy 2: Partial ID match with state="attached" + JS click
        if not onboarding_clicked:
            for alt_sel in [ASSIGN_ONBOARDING_BUTTON_ALT1, ASSIGN_ONBOARDING_BUTTON_ALT2]:
                try:
                    el = page.locator(alt_sel).first
                    await el.wait_for(state="attached", timeout=5000)
                    await el.evaluate("el => el.click()")
                    onboarding_clicked = True
                    logger.info(f"Onboarding button clicked via strategy 2 ({alt_sel})")
                    break
                except Exception as e:
                    logger.warning(f"Strategy 2 failed ({alt_sel}): {e}")

        # Strategy 3: Text-based — find pencil/edit icon near "Assign onboarding experience"
        if not onboarding_clicked:
            try:
                el = page.locator("text=Assign onboarding experience").locator("..").locator("a, button, [role='button']").first
                await el.wait_for(state="attached", timeout=5000)
                await el.evaluate("el => el.click()")
                onboarding_clicked = True
                logger.info("Onboarding button clicked via strategy 3 (text-based)")
            except Exception as e:
                logger.warning(f"Strategy 3 failed (text-based): {e}")

        # Strategy 4: JavaScript — find any clickable element within the onboarding section
        if not onboarding_clicked:
            try:
                clicked = await page.evaluate("""() => {
                    // Look for elements with 'assignedTemplate' in any attribute
                    const byId = document.querySelector('[id*="assignedTemplate"]');
                    if (byId) { byId.click(); return 'id-partial'; }
                    // Look for clickable element near the "Assign onboarding" text
                    const labels = document.querySelectorAll('*');
                    for (const el of labels) {
                        if (el.textContent && el.textContent.includes('Assign onboarding experience')
                            && el.children.length < 5) {
                            const clickable = el.querySelector('a, button, [role="button"], .edit-icon, [class*="edit"], [class*="pencil"]');
                            if (clickable) { clickable.click(); return 'text-child'; }
                            // Try clicking the parent area itself
                            el.click();
                            return 'text-parent';
                        }
                    }
                    return null;
                }""")
                if clicked:
                    onboarding_clicked = True
                    logger.info(f"Onboarding button clicked via strategy 4 (JS: {clicked})")
                else:
                    logger.warning("Strategy 4: no matching element found via JS")
            except Exception as e:
                logger.warning(f"Strategy 4 failed (JS): {e}")

        if not onboarding_clicked:
            # Capture diagnostic HTML dump for future debugging
            try:
                modal_html = await page.evaluate("""() => {
                    const modal = document.querySelector('[class*="modal"], [class*="dialog"], [role="dialog"]');
                    return modal ? modal.innerHTML.substring(0, 3000) : document.body.innerHTML.substring(0, 3000);
                }""")
                logger.error(f"All onboarding strategies failed. Modal HTML (first 3000 chars): {modal_html}")
            except Exception:
                pass
            raise FormSubmissionError("Could not click 'Assign onboarding experience' button after 4 strategies")

        # Wait for the onboarding experience assignment sub-page to load
        await page.wait_for_timeout(2000)

        # The onboarding template dropdown is an MDFSelectBox whose <input>
        # is hidden. The visible container div must be clicked to open the
        # dropdown menu — focusing the hidden input does not trigger React.
        ob_search_code = get_search_code(onboarding_experience)
        logger.info(f"Filling onboarding dropdown: search='{ob_search_code}', match='{onboarding_experience}'")

        await page.locator(ONBOARDING_TEMPLATE_SELECT).wait_for(state="attached", timeout=20000)

        # Click the visible MDFSelectBox container to open the dropdown.
        # Walk up from the hidden input to find the __control div.
        container_clicked = await page.evaluate("""() => {
            const input = document.querySelector('#onboardingTemplateId');
            if (!input) return 'no-input';
            // Try .closest() for the control wrapper
            const control = input.closest('[class*="MDFSelectBox__control"]');
            if (control) { control.click(); return 'control'; }
            // Walk up parents looking for the MDFSelectBox container
            let el = input.parentElement;
            for (let i = 0; i < 5 && el; i++) {
                const cls = el.className || '';
                if (cls.includes('MDFSelectBox')) { el.click(); return 'parent-' + i; }
                el = el.parentElement;
            }
            // Last resort: click the input's immediate parent
            if (input.parentElement) { input.parentElement.click(); return 'direct-parent'; }
            return 'nothing-found';
        }""")
        logger.info(f"Onboarding dropdown container click result: {container_clicked}")
        await page.wait_for_timeout(500)

        # Type search code via keyboard (dropdown should now be open/focused)
        await page.keyboard.type(ob_search_code)
        logger.debug(f"Typed '{ob_search_code}' into onboarding dropdown via keyboard")
        await page.wait_for_timeout(2000)

        ob_option = f'[class*="MDFSelectBox__option"]:has-text("{onboarding_experience}")'
        try:
            await page.wait_for_selector(ob_option, timeout=10000)
        except Exception:
            # Fallback: ArrowDown to force-open the menu, then retype
            logger.warning("Options not visible after container click + type, trying ArrowDown fallback")
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(500)
            await page.keyboard.press("Control+a")
            await page.keyboard.type(ob_search_code)
            await page.wait_for_timeout(2000)
            await page.wait_for_selector(ob_option, timeout=20000)

        await page.click(ob_option)
        await page.wait_for_timeout(500)
        logger.info(f"Selected onboarding experience: {onboarding_experience}")

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
