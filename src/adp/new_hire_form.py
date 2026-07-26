"""
New hire form automation.

Fills out and submits the ADP new hire form with validated data.
"""

import asyncio

from playwright.async_api import Page

from src.adp.base_form import click_visible_next_button, fill_date_field, fill_mdf_dropdown, fill_text_field
from src.adp.exceptions import FormSubmissionError
from src.config_tables import (
    JOB_TITLES,
    REASON_FOR_HIRE,
    TAX_ID_TYPE,
    WORK_SCHEDULE,
    get_everify_display_text,
    get_everify_location,
    get_home_department,
    get_manager,
    get_search_code,
    get_store_config,
)
from src.adp.selectors.new_hire import (
    ASSIGN_EXP_BUTTON,
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
    FORM_I9_ELECTRONIC,
    FIRST_NAME_INPUT,
    HIRE_DATE_INPUT,
    HOME_DEPARTMENT_SELECT,
    JOB_TITLE_SELECT,
    LAST_NAME_INPUT,
    MANAGER_NAME_SEARCH_INPUT,
    MANAGER_RADIO_CHECKED,
    MANAGER_RADIO_UNCHECKED,
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
    SEI_SELECT,
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
from src.utils.logger import setup_logger
from src.utils.screenshots import capture_screenshot

logger = setup_logger(__name__)


async def _select_onboarding_experience(
    page: Page, selector: str, search_code: str, experience_name: str, max_attempts: int = 3
) -> None:
    """Select onboarding experience from the MDFSelectBox dropdown with retry.

    The #onboardingTemplateId dropdown is a hidden MDFSelectBox input inside
    a slide-in panel that takes 5-15s to render on VPS. React Select opens
    on mousedown, not click. This function waits for the element to exist,
    then retries the open->search->select sequence.

    Args:
        page: Playwright page.
        selector: CSS selector for the dropdown input (ONBOARDING_TEMPLATE_SELECT).
        search_code: Text to type to filter options.
        experience_name: Full text of the option to select.
        max_attempts: Number of retry attempts.

    Raises:
        FormSubmissionError: If all attempts fail.
    """
    option_selector = f'[class*="MDFSelectBox__option"]:has-text("{experience_name}")'

    # Wait for the slide-in panel to fully render #onboardingTemplateId.
    # The panel takes 5-15s on VPS — must wait before any interaction.
    logger.info("Waiting for onboarding dropdown to appear in DOM...")
    try:
        await page.wait_for_selector(selector, state="attached", timeout=20000)
        logger.info("Onboarding dropdown element found in DOM")
    except Exception as e:
        # Panel didn't load — try re-clicking pencil icon
        logger.warning(f"Onboarding dropdown not found after 20s: {e}")
        logger.info("Re-clicking pencil icon to reopen slide-in panel")
        try:
            await page.locator("#assignedTemplateName_Id").evaluate("el => el.click()")
            await page.wait_for_timeout(5000)
            await page.wait_for_selector(selector, state="attached", timeout=20000)
            logger.info("Onboarding dropdown found after re-click")
        except Exception as e2:
            raise FormSubmissionError(
                f"Onboarding slide-in panel failed to load: {e2}"
            )

    for attempt in range(1, max_attempts + 1):
        logger.info(f"Onboarding dropdown attempt {attempt}/{max_attempts}")

        try:
            # Strategy 1: force-click the hidden input
            try:
                await page.locator(selector).click(force=True, timeout=5000)
                logger.info("Onboarding dropdown: force-click on input succeeded")
            except Exception as e:
                logger.info(f"Onboarding dropdown: force-click failed: {e}")

            await page.wait_for_timeout(500)

            # Strategy 2: dispatch focus + mousedown on the input
            # Guard with short timeout — element may not be interactive
            try:
                await asyncio.wait_for(
                    page.locator(selector).dispatch_event("focus"),
                    timeout=5.0
                )
                await asyncio.wait_for(
                    page.locator(selector).dispatch_event("mousedown"),
                    timeout=5.0
                )
                logger.info("Onboarding dropdown: dispatched focus + mousedown on input")
            except (asyncio.TimeoutError, Exception) as e:
                logger.info(f"Onboarding dropdown: dispatch events failed: {e}")

            await page.wait_for_timeout(500)

            # Strategy 3: dispatch mousedown on the MDFSelectBox container
            await page.evaluate("""(sel) => {
                const input = document.querySelector(sel);
                if (input) {
                    const container = input.closest('[class*="MDFSelectBox"]')
                        || input.parentElement;
                    container.scrollIntoView({block: 'center'});
                    container.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                }
            }""", selector)
            logger.info("Onboarding dropdown: dispatched mousedown on container")
            await page.wait_for_timeout(500)

            # Check if THIS dropdown's menu is now visible (scoped to container)
            menu_visible = await page.evaluate("""(sel) => {
                const input = document.querySelector(sel);
                if (!input) return false;
                const container = input.closest('[class*="MDFSelectBox"]')
                    || input.parentElement;
                const menu = container.querySelector('[class*="MDFSelectBox__menu"]');
                return menu !== null && menu.offsetHeight > 0;
            }""", selector)
            logger.info(f"Onboarding dropdown: menu visible = {menu_visible}")

            if not menu_visible and attempt < max_attempts:
                logger.warning(f"Dropdown menu not visible on attempt {attempt}, retrying...")
                # Clear input without closing the slide-in panel
                await page.evaluate("""(sel) => {
                    const input = document.querySelector(sel);
                    if (input) {
                        input.value = '';
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                    }
                }""", selector)
                await page.wait_for_timeout(1500)
                continue

            # Type search code and wait for option
            await page.keyboard.type(search_code)
            logger.info(f"Onboarding dropdown: typed '{search_code}'")

            # Use shorter timeout per attempt so retries happen faster
            option_timeout = 10000 if attempt < max_attempts else 20000
            await page.wait_for_selector(option_selector, timeout=option_timeout)
            await page.click(option_selector)
            await page.wait_for_timeout(500)
            logger.info(f"Selected onboarding experience: {experience_name}")
            return

        except Exception as e:
            logger.warning(f"Onboarding dropdown attempt {attempt} failed: {e}")
            if attempt == max_attempts:
                raise FormSubmissionError(
                    f"Failed to select onboarding experience after {max_attempts} attempts: {e}"
                )
            # Clear input value via JS — do NOT press Escape (closes slide-in panel)
            await page.evaluate("""(sel) => {
                const input = document.querySelector(sel);
                if (input) {
                    input.value = '';
                    input.blur();
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    // Close dropdown menu without closing slide-in panel
                    const menu = input.closest('[class*="MDFSelectBox"]')
                        ?.querySelector('[class*="MDFSelectBox__menu"]');
                    if (menu) menu.remove();
                }
            }""", selector)
            await page.wait_for_timeout(1500)


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
        await fill_mdf_dropdown(page, REASON_FOR_HIRE_SELECT, get_search_code(reason_label))
        logger.debug(f"Selected reason for hire: {reason_label}")

        # Select company code (from store config)
        company_code = store_config["company_code"]
        await fill_mdf_dropdown(page, COMPANY_CODE_SELECT, get_search_code(company_code))
        logger.debug(f"Selected company code: {company_code}")

        # Company code selection can trigger ADP to re-render dependent fields
        await page.wait_for_timeout(2000)

        # Select tax ID type (always SSN)
        await fill_mdf_dropdown(page, TAX_ID_TYPE_SELECT, "United States Social", timeout=20000)
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

        # Wait for any loading spinner to disappear before interacting
        try:
            spinner = page.locator(
                ".sdf-spinner, .vdl-spinner, [class*='spinner'], [class*='loading']"
            ).first
            await spinner.wait_for(state="hidden", timeout=15000)
            logger.info("Modal spinner disappeared")
        except Exception:
            logger.info("No modal spinner detected or already gone")

        # Click the pencil/edit icon (SDF-BUTTON#assignedTemplateName_Id, 14x16px
        # fa-pencil) to open the onboarding experience sub-page.
        # CRITICAL: Two "Assign onboarding experience" elements exist in the DOM:
        #   1. Header button #ENHAssignOnboarding (y=-662, above viewport — ignore)
        #   2. Visible modal label + pencil icon (y>0 — this is the target)
        # Must filter by viewport visibility to avoid clicking the off-screen one.

        # Scroll the modal into view — on VPS both text nodes have zero dimensions
        # because the modal panel is not scrolled into the viewport.
        await page.evaluate(
            "document.querySelector('#ENHAskNewhire, [class*=\"askNewHire\"], [class*=\"prehire\"]')"
            "?.scrollIntoView({block: 'center'})"
        )
        try:
            await page.locator("text=Assign onboarding experience").first.scroll_into_view_if_needed()
        except Exception:
            logger.info("Could not scroll 'Assign onboarding experience' into view")
        await page.wait_for_timeout(1000)

        try:
            click_result = await asyncio.wait_for(
                page.evaluate("""() => {
            const log = [];
            const isVisible = (el) => {
                const r = el.getBoundingClientRect();
                return r.top >= -100 && r.top < window.innerHeight && r.width > 0 && r.height > 0;
            };
            const rect = (el) => {
                const r = el.getBoundingClientRect();
                return Math.round(r.left) + ',' + Math.round(r.top) + ',' + Math.round(r.width) + 'x' + Math.round(r.height);
            };

            // Find visible "Assign onboarding experience" label
            const walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT,
                { acceptNode: n => n.textContent.includes('Assign onboarding experience')
                    ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT }
            );
            const nodes = [];
            let node;
            while ((node = walker.nextNode())) nodes.push(node);
            log.push('text_nodes=' + nodes.length);

            for (const tn of nodes) {
                const label = tn.parentElement;
                if (!label) continue;
                const vis = isVisible(label);
                log.push('label tag=' + label.tagName + ' id=' + (label.id || '') +
                         ' class=' + (String(label.className) || '').substring(0, 60) +
                         ' rect=' + rect(label) + ' visible=' + vis);
                if (!vis) continue;

                // Strategy A: click visible parent button/link
                const parentBtn = label.closest('button, a[href], [role="button"]');
                if (parentBtn && isVisible(parentBtn)) {
                    log.push('stratA: id=' + (parentBtn.id || '') + ' rect=' + rect(parentBtn));
                    parentBtn.scrollIntoView({block: 'center'});
                    parentBtn.click();
                    return { clicked: 'parent-button:' + (parentBtn.id || parentBtn.tagName), log: log };
                }
                log.push('stratA: no visible parent button');

                // Strategy B: find visible sibling (pencil icon) within 3 levels
                let container = label.parentElement;
                for (let depth = 0; depth < 3 && container; depth++) {
                    const children = container.querySelectorAll(
                        'a, button, svg, img, [role="button"], [class*="edit"], [class*="icon"]'
                    );
                    for (const c of children) {
                        if (c.contains(label) || label.contains(c)) continue;
                        if (!isVisible(c)) continue;
                        log.push('stratB: depth=' + depth + ' id=' + (c.id || '') +
                                 ' tag=' + c.tagName + ' class=' + (String(c.className) || '').substring(0, 60) +
                                 ' rect=' + rect(c));
                        c.scrollIntoView({block: 'center'});
                        c.click();
                        return { clicked: 'sibling:' + (c.id || c.tagName), log: log };
                    }
                    container = container.parentElement;
                }
                log.push('stratB: no visible sibling found');
            }

            log.push('all strategies failed');
            return { clicked: null, log: log };
        }"""),
                timeout=15
            )
        except asyncio.TimeoutError:
            logger.error("Onboarding pencil JS evaluate timed out after 15s")
            click_result = {"clicked": None, "log": ["JS evaluate timed out"]}
        except Exception as e:
            logger.error(f"Onboarding pencil JS evaluate failed: {e}")
            click_result = {"clicked": None, "log": [f"JS exception: {str(e)}"]}

        for line in click_result.get("log", []):
            logger.info(f"Onboarding click: {line}")

        if not click_result.get("clicked"):
            raise FormSubmissionError(
                "Could not click 'Assign onboarding experience' pencil icon"
            )
        logger.info(f"Onboarding pencil icon clicked via {click_result['clicked']}")

        # Wait for onboarding sub-page slide-in to load
        await page.wait_for_timeout(5000)

        # Select onboarding experience from MDFSelectBox (#onboardingTemplateId)
        # inside the slide-in pane (#showTemplateSlideIn_Id)
        logger.info(f"Selecting onboarding experience: {onboarding_experience}")

        ob_search_code = get_search_code(onboarding_experience)
        logger.info(f"Onboarding MDF dropdown: search='{ob_search_code}', match='{onboarding_experience}'")

        await _select_onboarding_experience(
            page, ONBOARDING_TEMPLATE_SELECT, ob_search_code, onboarding_experience
        )

        # Click "Assign" button then "Back" to return to the modal
        await page.wait_for_selector(ASSIGN_EXP_BUTTON, timeout=20000)
        await page.locator(ASSIGN_EXP_BUTTON).evaluate("el => el.click()")
        await page.wait_for_timeout(1000)
        await page.wait_for_selector(BACK_BUTTON, timeout=20000)
        await page.locator(BACK_BUTTON).evaluate("el => el.click()")
        logger.info(f"Assigned onboarding experience: {onboarding_experience}")

        # Select Worked In State (from store config)
        worked_in_state = store_config["worked_in_state"]
        logger.info(f"Selecting worked in state: {worked_in_state}")
        await fill_mdf_dropdown(page, WORKED_IN_STATE_SELECT, get_search_code(worked_in_state))
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

            # Wait for results to render
            await page.wait_for_selector(
                MANAGER_RADIO_UNCHECKED, timeout=20000
            )

            # Click the first unchecked radio button in the results
            logger.info("Clicking first radio button in results")
            await page.click(MANAGER_RADIO_UNCHECKED)

            # Verify selection took effect
            await page.wait_for_timeout(500)
            checked_count = await page.locator(MANAGER_RADIO_CHECKED).count()
            if checked_count > 0:
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

        # Select SEI (Self Employment Individual) - always N/A for hourly/salary employees
        logger.info("Selecting SEI: N/A - Not Applicable")
        try:
            await fill_mdf_dropdown(page, SEI_SELECT, "N/A")
            logger.debug("Selected SEI: N/A - Not Applicable")
        except Exception as e:
            warn_msg = f"SEI selection failed: {e} — continuing without SEI"
            logger.warning(warn_msg)
            warnings.append(warn_msg)

        # Form I-9 selection: "Yes, electronically" (legal requirement, hard-fail).
        # Must occur AFTER SEI — ADP clears any default I-9 selection once SEI is
        # filled, leaving the field blank. ADP locks this field after the modal
        # saves (per ADP's "won't be able to change your selections for SEI or the
        # Form I-9 question" warning), so getting it wrong is a compliance
        # violation that cannot be corrected post-submit.
        # NOTE: page.click() on the wfn-radio-button wrapper fires the event but
        # the custom element doesn't propagate it to the inner sdf-radio-button —
        # Playwright reports success but the radio stays unselected, the modal
        # save validation fails, and the next-section click times out.
        # Use locator.evaluate("el => el.click()") to fire the click in the
        # element's own JS context. Same pattern used for Assign/Back buttons
        # in the onboarding sub-flow and for the Use for Notification checkbox.
        logger.info("Selecting Form I-9: Yes, electronically")
        try:
            await page.wait_for_selector(FORM_I9_ELECTRONIC, timeout=20000)
            await page.locator(FORM_I9_ELECTRONIC).evaluate("el => el.click()")
        except Exception as e:
            raise FormSubmissionError(
                f"Form I-9 selection failed for "
                f"{hire.first_name} {hire.last_name}: expected 'Yes, electronically'"
            ) from e

        # E-Verify location is a legal I-9 requirement — hard-fail on mismatch
        display_text = get_everify_display_text(hire.store_number)
        logger.info(f"Filling E-Verify location: {display_text}")
        try:
            state_prefix = display_text.split(" - ", 1)[0]  # "TX" or "CO"
            await fill_mdf_dropdown(
                page,
                E_VERIFY_LOCATION_SELECT,
                search_code=state_prefix,
                exact_text=display_text,
            )
        except Exception as e:
            raise FormSubmissionError(
                f"E-Verify location match failed for store "
                f"{hire.store_number}: expected '{display_text}'"
            ) from e


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
        logger.info(f"Filling Job Title with value: {job_title_label}")
        await fill_mdf_dropdown(page, JOB_TITLE_SELECT, get_search_code(job_title_label))

        # Worker Category (resolve from config_tables)
        worker_category_label = WORK_SCHEDULE[hire.work_schedule]
        logger.info(f"Filling Worker Category with value: {worker_category_label}")
        await fill_mdf_dropdown(page, WORKER_CATEGORY_SELECT, get_search_code(worker_category_label))

        # Benefits Eligibility Class (from store config)
        benefits_eligibility = store_config["benefits_eligibility"]
        logger.info(f"Filling Benefits Eligibility Class with value: {benefits_eligibility}")
        await fill_mdf_dropdown(page, BENEFITS_ELIGIBILITY_CLASS_SELECT, "BE")

        # Calculate Using Measurement Periods radio (from store config)
        if store_config["measurement_periods"]:
            await page.wait_for_selector(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO, timeout=20000)
            await page.click(CALCULATE_USING_MEASUREMENT_PERIODS_RADIO)
            logger.debug("Selected measurement periods option")

        # Home Department (auto-derived from store number + job title)
        home_department = get_home_department(hire.store_number, hire.job_title)
        logger.info(f"Filling Home Department with value: {home_department}")
        await fill_mdf_dropdown(page, HOME_DEPARTMENT_SELECT, home_department)

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

        # Compensation Type (always Hourly). Search code MUST be "Hourly"
        # not "Hour" — fill_mdf_dropdown anchors with `^\s*{code}\b` and
        # the word boundary fails mid-word (no boundary between "Hour"
        # and "ly"). Using the full word lets `\b` anchor at end-of-string.
        logger.info("Filling Compensation Type with value: Hourly")
        await fill_mdf_dropdown(page, COMPENSATION_TYPE_SELECT, "Hourly")

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
        await fill_mdf_dropdown(page, SUI_SDI_TAX_CODE_SELECT, get_search_code(worked_in_state))
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
