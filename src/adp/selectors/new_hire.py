"""ADP new hire form selectors - Real selectors from ADP Workforce Now."""

# ============================================================================
# NAVIGATION SELECTORS
# ============================================================================

# Process menu navigation
PROCESS_MENU_BUTTON = 'button:has-text("Process")'
HIRE_REHIRE_LINK = 'a[href="#/Process/ProcessTabHRCategoryHireRehire"]'
GO_TO_HIRE_BUTTON = '#navigateToNewHireViewId'
HR_PR_NEW_HIRES_CARD = 'sdf-box:has-text("HR PR New Hires")'

# ============================================================================
# PERSONAL INFORMATION SECTION
# ============================================================================

# Basic info fields
FIRST_NAME_INPUT = '#Name\\.first'
FIRST_NAME_INPUT_ALT = 'input[name="firstName"]'
LAST_NAME_INPUT = '#Name\\.last'
LAST_NAME_INPUT_ALT = 'input[name="lastName"]'
PHONE_INPUT = '#rec_textbox_mobile'
PHONE_INPUT_ALT = 'input[data-testid="phone-input"]'
USE_FOR_NOTIFICATION_CHECKBOX = 'input[name="useFrNotifyOnChangeId"]'
PERSONAL_EMAIL_INPUT = '#homeEmail'
PERSONAL_EMAIL_INPUT_ALT = 'input[name="homeEmail"]'
HIRE_DATE_INPUT = '#HireDate'
HIRE_DATE_INPUT_ALT = 'input[name="hireDate"]'
REASON_FOR_HIRE_SELECT = '#ReasonForHire'
COMPANY_CODE_SELECT = '#CompanyCode'
TAX_ID_TYPE_SELECT = '#TaxIdComponent_taxidtype'

# Associate ID (auto-generated, MUST CAPTURE)
ASSOCIATE_ID_INPUT = '#AssociateID'
ASSOCIATE_ID_INPUT_ALT = 'input[name="assocId"]'

# ============================================================================
# ASK THE NEW HIRE MODAL
# ============================================================================

# Modal opener
ASK_NEW_HIRE_BUTTON = '#ENHAskNewhire'

# Onboarding experience assignment
ASSIGN_ONBOARDING_BUTTON = '#assignedTemplateName_Id'
ASSIGN_ONBOARDING_BUTTON_ALT1 = '[id*="assignedTemplate"]'
ASSIGN_ONBOARDING_BUTTON_ALT2 = 'a[id*="assignedTemplate"]'
ONBOARDING_TEMPLATE_SELECT = '#onboardingTemplateId'
ASSIGN_EXP_BUTTON = '#ENHAssignOBExp'
BACK_BUTTON = '#back-button-with-label'

# Worked in state
WORKED_IN_STATE_SELECT = '#workedInState'

# Reports to (manager)
REPORTS_TO_BUTTON = '#openReportsToCustomSlider_Id'
MANAGER_NAME_SEARCH_INPUT = '#onReportsToSearch'
MANAGER_SEARCH_BUTTON = '#reportsToSearch_Id'
MANAGER_RADIO_BUTTON = 'sdf-radio-button[aria-checked="true"]'
SAVE_MANAGER_BUTTON = '#populateReportToValue_Id'

# E-Verify work location
E_VERIFY_LOCATION_SELECT = '#eVerifyLocationSelectBox'

# Form I-9 indicator (electronically). Two issues this selector handles:
#
# 1. EN-DASH TRAP. The id contains an en-dash (U+2013, written as \u2013),
#    NOT a regular hyphen (U+002D). They look nearly identical but are
#    different Unicode characters. The \u2013 escape is used here to make
#    this trap explicit and grep-safe. Do NOT replace with a literal
#    hyphen — selector will silently fail. The "I-9" itself uses regular
#    hyphens (only the dash between "question" and "electronic" is en).
#
# 2. DUPLICATE ID IN DOM. ADP renders this same id in two places:
#    a) Inside #showPreHireModal_Id ("Ask the New Hire" modal — target)
#    b) Inside #Employment (a read-only/disabled mirror that ADP populates
#       from the modal selection — NOT clickable)
#    Without the #showPreHireModal_Id prefix, Playwright strict mode
#    raises "resolved to 2 elements" and the click fails. The modal is
#    the source of truth; the Employment copy is just a display.
FORM_I9_ELECTRONIC = '#showPreHireModal_Id wfn-radio-button[id="Form I-9 question \u2013 electronic"]'

# Self Employment Individual (SEI)
SEI_SELECT = '#selfEmpIndList_Id'

# Save modal
SAVE_MODAL_BUTTON = '#ENHInitiatePrehire'

# ============================================================================
# PROCEEDING/NEXT BUTTON SELECTORS
# ============================================================================

# After personal section
NEXT_BUTTON_PRIMARY = '#OE_Next_Prim_btn_Id'
VALIDATION_POPUP_GO_TO_NEXT = 'sdf-button[aria-label="Go to Next Section"]'
VALIDATION_POPUP_GO_TO_NEXT_ALT = 'button:has-text("Go to Next Section")'

# ============================================================================
# EMPLOYMENT SECTION
# ============================================================================

JOB_TITLE_SELECT = '#jobTitleList_Id_div'
JOB_TITLE_SELECT_ALT = 'input[aria-label="Job Title"]'
WORKER_CATEGORY_SELECT = '#workersCategry_Id'
WORKER_CATEGORY_SELECT_ALT = 'input[aria-label="Worker Category"]'
BENEFITS_ELIGIBILITY_CLASS_SELECT = '#benEligClassList_Id'
BENEFITS_ELIGIBILITY_CLASS_SELECT_ALT = 'input[aria-label="Benefits Eligibility Class"]'
CALCULATE_USING_MEASUREMENT_PERIODS_RADIO = 'sdf-radio-button[value="C"]'
HOME_DEPARTMENT_SELECT = '#homeDep_Id'
HOME_DEPARTMENT_SELECT_ALT = 'input[aria-label="Home Department"]'

# Next button after employment
EMPLOYMENT_NEXT_BUTTON = 'button.vdl-button--primary:has-text("Next")'
EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT = 'sdf-button[aria-label="Go to Next Section"]'
EMPLOYMENT_VALIDATION_POPUP_GO_TO_NEXT_ALT = 'button:has-text("Go to Next Section")'

# ============================================================================
# PAYROLL SECTION
# ============================================================================

COMPENSATION_TYPE_SELECT = '#regPayRate'
REGULAR_PAY_RATE_INPUT = '#SalaryPerPay'
REGULAR_PAY_RATE_INPUT_ALT = 'input[name="payName"]'

# Next button after payroll
PAYROLL_NEXT_BUTTON = 'button.vdl-button--primary:has-text("Next")'

# ============================================================================
# TAX SECTION
# ============================================================================

SUI_SDI_TAX_CODE_SELECT = '#suisdiTax'
SUI_SDI_TAX_CODE_SELECT_ALT = 'input[aria-label="SUI/SDI Tax Code"]'

# Next button after tax
TAX_NEXT_BUTTON = '#taxNext_Id'
TAX_NEXT_BUTTON_ALT = 'button[name="taxNext"]'

# ============================================================================
# DIRECT DEPOSIT SECTION (OPTIONAL)
# ============================================================================

DEDUCTION_CODE_SELECT = '#deductionCodeId__0'
VERIFY_ACCOUNT_TOGGLE = '#bypassPrenoteToggleSwitch_0'
VERIFY_ACCOUNT_TOGGLE_ALT = 'input[name="bypassPrenote_0"]'
ROUTING_NUMBER_INPUT = '#transitABANumber_0'
ROUTING_NUMBER_INPUT_ALT = 'input[aria-label="Routing Number"]'
ACCOUNT_NUMBER_INPUT = '#bankDepAccNumber_0'
ACCOUNT_NUMBER_INPUT_ALT = 'input[aria-label="Account Number"]'

# Next button after direct deposit
DD_NEXT_BUTTON = 'button[name="ddNext"]'

# ============================================================================
# EMERGENCY CONTACT SECTION (SKIP)
# ============================================================================

EMERGENCY_CONTACT_NEXT_BUTTON = 'button.vdl-button--primary:has-text("Next")'

# ============================================================================
# IN-PROGRESS HIRES / EMAIL CHANGE
# ============================================================================

IN_PROGRESS_TAB = 'li[role="tab"]:has-text("In-Progress Hires")'
IN_PROGRESS_SEARCH = '#searchInProgressValue'

# ============================================================================
# SAVE AND EXIT
# ============================================================================

SAVE_AND_EXIT_BUTTON = '#ENHSaveAndExit'

# ============================================================================
# REGISTRATION CODE DELIVERY
# ============================================================================

# Navigate to Security Management
SETUP_MENU_BUTTON = 'button:has-text("Setup")'
SECURITY_MANAGEMENT_LINK = 'a[href="#/pracSetup/pracSecurityManagement"]'

# People menu navigation (Dojo framework)
PEOPLE_MENU = '#People_navItem'
PEOPLE_MENU_LABEL = 'span[id="People_navItem_label"]'
PERSONAL_REGISTRATION_CODES_LINK = '#People_ttd_Access\\&Security_PersonalRegistrationCodes'
PERSONAL_REGISTRATION_CODES_LINK_ALT = 'span[href="/revadm/strong/people/pic/picManagement.faces"]'

# Search fields
LAST_NAME_SEARCH_INPUT = '#userLastName'
LAST_NAME_SEARCH_INPUT_ALT = 'input[name="searchform:userLastName"]'
FIRST_NAME_SEARCH_INPUT = '#userFirstName'
FIRST_NAME_SEARCH_INPUT_ALT = 'input[name="searchform:userFirstName"]'
ASSOCIATE_ID_SEARCH_INPUT = '#empId'
ASSOCIATE_ID_SEARCH_INPUT_ALT = 'input[name="searchform:empId"]'
SEARCH_BUTTON = '#formSaveButton'
SEARCH_BUTTON_ALT = 'input[name="searchform:formSaveButton"]'

# Employee selection and code delivery
EMPLOYEE_CHECKBOX = 'img[id="tableGrid.store.rows[0].cells[0]_widget"]'
ISSUE_PRC_DROPDOWN = '#picEmailActions_arrow'
ISSUE_PRC_DROPDOWN_ALT = 'span[name="searchResultform:picEmailActions"]'
PERSONAL_EMAIL_OPTION = '#picPersonalEmailMenuItem'
PERSONAL_EMAIL_OPTION_ALT = 'tr[aria-label*="Personal Email Address"]'
WORK_EMAIL_OPTION = '#picWorkEmailMenuItem'
VIEW_CODES_OPTION = '#picWorkOnScreenMenuItem'
CONFIRMATION_YES_BUTTON = 'span[role="button"]:has(span.dijitButtonText:has-text("Yes"))'
CONFIRMATION_YES_BUTTON_ALT = 'span.dijitButtonText:has-text("Yes")'

# PRC email update selectors
PRC_SAVE_CHANGES = '#tableGridSaveButton'
PRC_PERSONAL_COLUMN_HEADER = '#tableGrid_header_3'
