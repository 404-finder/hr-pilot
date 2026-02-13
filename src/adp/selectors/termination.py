"""
ADP termination form selectors.

CRITICAL: These are PLACEHOLDER selectors. Must be updated by inspecting
the live ADP termination workflow with browser DevTools.
"""

# TODO: Update all selectors after inspecting live ADP page
# Employee search
EMPLOYEE_SEARCH_INPUT = "#employeeSearch"  # PLACEHOLDER
SEARCH_BUTTON = "button[data-action='search']"  # PLACEHOLDER
EMPLOYEE_RESULT = ".employee-search-result:first-child"  # PLACEHOLDER

# Actions menu
ACTIONS_MENU = "#actionsMenu"  # PLACEHOLDER
TERMINATE_ACTION = "[data-action='terminate']"  # PLACEHOLDER

# Termination form
TERMINATION_FORM = "#terminationForm"  # PLACEHOLDER
TERMINATION_DATE_INPUT = "#terminationDate"  # PLACEHOLDER
LAST_WORK_DATE_INPUT = "#lastWorkDate"  # PLACEHOLDER
TERMINATION_REASON_SELECT = "#terminationReason"  # PLACEHOLDER
TERMINATION_TYPE_SELECT = "#terminationType"  # PLACEHOLDER
ELIGIBLE_FOR_REHIRE_CHECKBOX = "#eligibleForRehire"  # PLACEHOLDER
FINAL_PAY_DATE_INPUT = "#finalPayDate"  # PLACEHOLDER
PAYOUT_PTO_CHECKBOX = "#payoutPto"  # PLACEHOLDER
NOTES_INPUT = "#terminationNotes"  # PLACEHOLDER

# Review & submit
REVIEW_BUTTON = "button[data-action='review']"  # PLACEHOLDER
REVIEW_CONFIRMATION = ".review-confirmation"  # PLACEHOLDER
SUBMIT_BUTTON = "button[data-action='submit']"  # PLACEHOLDER
SUCCESS_BANNER = ".success-notification"  # PLACEHOLDER
