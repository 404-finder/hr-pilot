# CLAUDE.md — hr-pilot: Telegram-to-ADP HR Automation
## User Interaction
-   Be concise and professional in your responses
-   Present code first then explain your code
-   Ask clarifying questions when you are unsure
-   Favor readability over fancy solutions
-   Print statements in code are short yet informative

## Project Overview

Build a Python automation system called **hr-pilot** that:

1. **Receives Telegram messages** containing HR action requests via a Telegram Bot.
2. **Parses messages** into structured data using Pydantic models.
3. **Logs into ADP Workforce Now** at `https://online.adp.com/signin/v1/?APPID=WFNPortal&productId=80e309c3-7085-bae1-e053-3505430b5495&returnURL=https://workforcenow.adp.com/&callingAppId=WFN` using browser automation.
4. **Fills out the appropriate ADP form** (new hire or termination) with the parsed data.
5. **Reports status** back to Telegram (success/failure with screenshots on error).


### Supported Workflows

| Command | ADP Action | Description |
|---|---|---|
| `/newhire` | Add New Hire | Enter a new employee into ADP WFN |
| `/terminate` | Terminate Employee | Process an employee termination in ADP WFN |

---

## Tech Stack

| Component | Library | Purpose |
|---|---|---|
| Telegram Bot | `python-telegram-bot` (v20+) | Async bot to receive/send messages |
| Browser Automation | `playwright` | Headless browser to interact with ADP |
| Config Management | `python-dotenv` | Store secrets in `.env` |
| Data Validation | `pydantic` (v2+) | Validate/parse HR data models |
| MFA Handling | `pyotp` | TOTP-based MFA for ADP login |
| Logging | `logging` (stdlib) | Structured logging throughout |

---

## Project Structure

```
hr-pilot/
├── CLAUDE.md                      # This file
├── .env                           # Secrets (DO NOT COMMIT)
├── .env.example                   # Template for .env
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point — starts Telegram bot
│   ├── config.py                  # Load env vars, app settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # Shared base model, enums, types
│   │   ├── new_hire.py            # Pydantic model for new hire data
│   │   └── termination.py         # Pydantic model for termination data
│   ├── telegram_bot/
│   │   ├── __init__.py
│   │   ├── bot.py                 # Bot setup, handler registration
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── common.py          # /start, /help, /cancel, error handler
│   │   │   ├── new_hire.py        # /newhire command + conversation flow
│   │   │   └── termination.py     # /terminate command + conversation flow
│   │   └── parsers.py             # Parse telegram messages → Pydantic models
│   ├── adp/
│   │   ├── __init__.py
│   │   ├── auth.py                # ADP login/logout, session management
│   │   ├── base_form.py           # Shared form-filling utilities
│   │   ├── navigation.py          # Navigate ADP menus and pages
│   │   ├── new_hire_form.py       # New hire form automation
│   │   ├── termination_form.py    # Termination form automation
│   │   └── selectors/
│   │       ├── __init__.py
│   │       ├── login.py           # Login page selectors
│   │       ├── new_hire.py        # New hire form selectors
│   │       └── termination.py     # Termination form selectors
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       ├── encryption.py          # Encrypt/decrypt sensitive data at rest
│       └── screenshots.py         # Debug screenshot capture helper
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared pytest fixtures
│   ├── test_parsers.py
│   ├── test_models.py
│   ├── test_adp_auth.py
│   ├── test_new_hire_form.py
│   └── test_termination_form.py
└── screenshots/                   # Debug screenshots on failure (gitignored)
```

---

## Environment Variables (`.env`)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321  # Whitelist authorized users

# ADP Credentials
ADP_USERNAME=your-adp-username
ADP_PASSWORD=your-adp-password
ADP_MFA_SECRET=your-totp-secret  # If ADP uses TOTP-based MFA

# App Settings
LOG_LEVEL=INFO
HEADLESS=true  # Run browser in headless mode
SCREENSHOT_DIR=screenshots
```

---

## Coding Standards

- Follow **PEP 8** strictly (https://peps.python.org/pep-0008/).
- Use **type hints** on all function signatures and return types.
- Use **`async`/`await`** throughout — `python-telegram-bot` v20+ and Playwright async API.
- All sensitive data (passwords, SSNs) must be handled securely:
  - Never log sensitive fields.
  - Use `pydantic.SecretStr` for passwords and SSNs in models.
  - Clear browser session data after each automation run.
- Write **docstrings** for all public functions and classes (Google style).
- Keep functions small and single-purpose.
- Use `logging` module — never `print()`.
- Constants in `UPPER_SNAKE_CASE`, classes in `PascalCase`, functions/variables in `snake_case`.
- All packages must be installed in the virtual environment `.venv`
---

## Data Models

### `NewHire` (`src/models/new_hire.py`)

```python
from datetime import date

from pydantic import BaseModel, SecretStr, field_validator


class NewHire(BaseModel):
    """Represents a new hire to be entered into ADP."""

    first_name: str
    last_name: str
    ssn: SecretStr
    date_of_birth: date
    email: str
    phone: str
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    zip_code: str
    job_title: str
    department: str
    pay_rate: float
    pay_frequency: str  # "hourly" | "salary"
    start_date: date
    manager: str | None = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError("State must be a 2-letter abbreviation")
        return v.upper()

    @field_validator("pay_frequency")
    @classmethod
    def validate_pay_frequency(cls, v: str) -> str:
        allowed = {"hourly", "salary"}
        if v.lower() not in allowed:
            raise ValueError(f"Pay frequency must be one of: {allowed}")
        return v.lower()
```

### `Termination` (`src/models/termination.py`)

```python
from datetime import date

from pydantic import BaseModel, field_validator


class Termination(BaseModel):
    """Represents an employee termination to be processed in ADP."""

    # Employee identification
    first_name: str
    last_name: str
    employee_id: str  # ADP employee/position ID

    # Termination details
    termination_date: date
    last_work_date: date
    termination_reason: str  # e.g., "Voluntary", "Involuntary", "Resignation"
    termination_type: str  # e.g., "Standard", "Retirement", "End of Contract"
    eligible_for_rehire: bool = True

    # Final pay
    final_pay_date: date | None = None
    payout_pto: bool = False  # Pay out remaining PTO

    # Additional info
    notes: str | None = None

    @field_validator("termination_reason")
    @classmethod
    def validate_termination_reason(cls, v: str) -> str:
        allowed = {
            "voluntary",
            "involuntary",
            "resignation",
            "retirement",
            "end of contract",
            "mutual agreement",
            "job abandonment",
            "layoff",
            "death",
        }
        if v.lower() not in allowed:
            raise ValueError(
                f"Termination reason must be one of: {allowed}"
            )
        return v.lower()

    @field_validator("termination_type")
    @classmethod
    def validate_termination_type(cls, v: str) -> str:
        allowed = {
            "standard",
            "retirement",
            "end of contract",
            "reduction in force",
        }
        if v.lower() not in allowed:
            raise ValueError(
                f"Termination type must be one of: {allowed}"
            )
        return v.lower()
```

### `Base` (`src/models/base.py`)

```python
from enum import Enum


class ActionType(str, Enum):
    """Supported HR automation actions."""

    NEW_HIRE = "new_hire"
    TERMINATION = "termination"


class ActionStatus(str, Enum):
    """Status of an automation run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
```

---

## Telegram Message Formats

### `/newhire` Command

```
/newhire
First Name: John
Last Name: Doe
SSN: 123-45-6789
Email: john.doe@company.com
Phone: 555-123-4567
Job Title: Crew
Pay Rate: 85000
Pay Type: salary
Start Date: 03/01/2026
Manager: Jane Smith
Store Location: North Valley Mills
Hiring Experience: Texas
```

### `/terminate` Command

```
/terminate
First Name: John
Last Name: Doe
Employee ID: 00123456
Termination Date: 03/15/2026
Last Work Date: 03/14/2026
Reason: Resignation
Type: Standard
Eligible for Rehire: Yes
Payout PTO: Yes
Notes: Employee accepted position at another company.
```

---

## Key Implementation Details

### 1. Telegram Bot (`src/telegram_bot/bot.py`)

- Use `python-telegram-bot` v20+ with `ApplicationBuilder` pattern.
- Register handlers for `/newhire`, `/terminate`, `/start`, `/help`, `/cancel`.
- Use `ConversationHandler` for guided multi-step input with validation at each step.
- **Security**: Only allow whitelisted `TELEGRAM_ALLOWED_USER_IDS` to trigger automation.
- Send status updates: "Processing termination for John Doe..." → final result.

```python
from telegram.ext import ApplicationBuilder, CommandHandler

from src.config import settings
from src.telegram_bot.handlers.common import start, help_command, cancel
from src.telegram_bot.handlers.new_hire import new_hire_conversation
from src.telegram_bot.handlers.termination import termination_conversation


def create_bot() -> None:
    """Build and start the Telegram bot."""
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(new_hire_conversation())
    app.add_handler(termination_conversation())

    app.run_polling()
```

### 2. ADP Login (`src/adp/auth.py`)

- Use `playwright.async_api.async_playwright`.
- Navigate to the ADP sign-in URL.
- Fill username → click next → fill password → click sign in.
- Handle MFA if present (TOTP via `pyotp` library).
- Wait for successful redirect to WFN dashboard.
- **Retry logic**: Retry login up to 3 times with exponential backoff on failure.
- **Session reuse**: Keep browser context alive between form submissions if multiple actions are queued.

```python
import pyotp
from playwright.async_api import async_playwright, Page

from src.adp.selectors.login import (
    USERNAME_INPUT,
    PASSWORD_INPUT,
    NEXT_BUTTON,
    SIGN_IN_BUTTON,
    MFA_INPUT,
)
from src.config import settings


async def login_to_adp() -> Page:
    """Log into ADP WFN and return the authenticated page.

    Returns:
        Authenticated Playwright Page object.

    Raises:
        LoginError: If login fails after max retries.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=settings.headless)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(settings.adp_login_url)
    await page.fill(USERNAME_INPUT, settings.adp_username)
    await page.click(NEXT_BUTTON)
    await page.fill(PASSWORD_INPUT, settings.adp_password)
    await page.click(SIGN_IN_BUTTON)

    # Handle MFA if prompted
    if settings.adp_mfa_secret:
        totp = pyotp.TOTP(settings.adp_mfa_secret)
        await page.fill(MFA_INPUT, totp.now())
        await page.click(SIGN_IN_BUTTON)

    await page.wait_for_url("**/workforcenow.adp.com/**", timeout=30000)
    return page
```

### 3. ADP Navigation (`src/adp/navigation.py`)

- Centralize all menu/page navigation logic.
- Both new hire and termination forms require navigating ADP's menu system to reach the correct page.
- Use `page.wait_for_selector` and `page.wait_for_load_state` to handle ADP's async page loads.

```python
from playwright.async_api import Page


async def navigate_to_new_hire(page: Page) -> None:
    """Navigate from ADP dashboard to the Add New Hire page."""
    # ADP menu path: People > Add New Hire
    # Implementation depends on actual ADP menu structure
    pass


async def navigate_to_termination(page: Page) -> None:
    """Navigate from ADP dashboard to the Termination page.

    Typically: search employee → open profile → Actions → Terminate.
    """
    pass
```

### 4. Shared Form Utilities (`src/adp/base_form.py`)

Reusable helpers for both forms:

```python
from playwright.async_api import Page


async def fill_text_field(page: Page, selector: str, value: str) -> None:
    """Clear and fill a text input field."""
    await page.wait_for_selector(selector, timeout=10000)
    await page.fill(selector, "")
    await page.fill(selector, value)


async def select_dropdown(
    page: Page, selector: str, value: str
) -> None:
    """Select an option from a dropdown by visible text."""
    await page.wait_for_selector(selector, timeout=10000)
    await page.select_option(selector, label=value)


async def fill_date_field(
    page: Page, selector: str, date_str: str
) -> None:
    """Fill a date picker field (MM/DD/YYYY format)."""
    await page.wait_for_selector(selector, timeout=10000)
    await page.fill(selector, "")
    await page.fill(selector, date_str)
    await page.keyboard.press("Tab")  # Trigger date validation


async def click_checkbox(
    page: Page, selector: str, should_check: bool
) -> None:
    """Set a checkbox to checked or unchecked."""
    await page.wait_for_selector(selector, timeout=10000)
    is_checked = await page.is_checked(selector)
    if is_checked != should_check:
        await page.click(selector)
```

### 5. New Hire Form (`src/adp/new_hire_form.py`)

```python
from playwright.async_api import Page

from src.adp.base_form import fill_text_field, select_dropdown, fill_date_field
from src.adp.navigation import navigate_to_new_hire
from src.adp.selectors.new_hire import *
from src.models.new_hire import NewHire
from src.utils.screenshots import capture_screenshot


async def fill_new_hire_form(page: Page, hire: NewHire) -> bool:
    """Fill out the ADP new hire form.

    Args:
        page: Authenticated ADP page.
        hire: Validated new hire data.

    Returns:
        True if form submitted successfully, False otherwise.
    """
    try:
        await navigate_to_new_hire(page)

        await fill_text_field(page, FIRST_NAME_INPUT, hire.first_name)
        await fill_text_field(page, LAST_NAME_INPUT, hire.last_name)
        await fill_text_field(
            page, SSN_INPUT, hire.ssn.get_secret_value()
        )
        await fill_date_field(
            page, DOB_INPUT, hire.date_of_birth.strftime("%m/%d/%Y")
        )
        await fill_text_field(page, EMAIL_INPUT, hire.email)
        await fill_text_field(page, PHONE_INPUT, hire.phone)
        await fill_text_field(
            page, ADDRESS_LINE_1_INPUT, hire.address_line_1
        )
        if hire.address_line_2:
            await fill_text_field(
                page, ADDRESS_LINE_2_INPUT, hire.address_line_2
            )
        await fill_text_field(page, CITY_INPUT, hire.city)
        await select_dropdown(page, STATE_SELECT, hire.state)
        await fill_text_field(page, ZIP_INPUT, hire.zip_code)
        await fill_text_field(page, JOB_TITLE_INPUT, hire.job_title)
        await select_dropdown(page, DEPARTMENT_SELECT, hire.department)
        await fill_text_field(
            page, PAY_RATE_INPUT, str(hire.pay_rate)
        )
        await select_dropdown(
            page, PAY_FREQUENCY_SELECT, hire.pay_frequency
        )
        await fill_date_field(
            page, START_DATE_INPUT,
            hire.start_date.strftime("%m/%d/%Y"),
        )

        # Submit
        await page.click(SUBMIT_BUTTON)
        await page.wait_for_selector(
            SUCCESS_BANNER, timeout=15000
        )
        return True

    except Exception as e:
        await capture_screenshot(page, "new_hire_error")
        raise
```

### 6. Termination Form (`src/adp/termination_form.py`)

```python
from playwright.async_api import Page

from src.adp.base_form import (
    fill_text_field,
    select_dropdown,
    fill_date_field,
    click_checkbox,
)
from src.adp.navigation import navigate_to_termination
from src.adp.selectors.termination import *
from src.models.termination import Termination
from src.utils.screenshots import capture_screenshot


async def fill_termination_form(
    page: Page, term: Termination
) -> bool:
    """Fill out the ADP termination form.

    Args:
        page: Authenticated ADP page.
        term: Validated termination data.

    Returns:
        True if form submitted successfully, False otherwise.

    Typical ADP termination workflow:
        1. Search for employee by ID or name.
        2. Open employee profile.
        3. Click Actions → Terminate.
        4. Fill termination details form.
        5. Review and submit.
    """
    try:
        await navigate_to_termination(page)

        # Step 1: Search and select the employee
        await fill_text_field(
            page, EMPLOYEE_SEARCH_INPUT, term.employee_id
        )
        await page.click(SEARCH_BUTTON)
        await page.wait_for_selector(
            EMPLOYEE_RESULT, timeout=10000
        )
        await page.click(EMPLOYEE_RESULT)

        # Step 2: Open termination action
        await page.click(ACTIONS_MENU)
        await page.click(TERMINATE_ACTION)
        await page.wait_for_selector(
            TERMINATION_FORM, timeout=10000
        )

        # Step 3: Fill termination details
        await fill_date_field(
            page, TERMINATION_DATE_INPUT,
            term.termination_date.strftime("%m/%d/%Y"),
        )
        await fill_date_field(
            page, LAST_WORK_DATE_INPUT,
            term.last_work_date.strftime("%m/%d/%Y"),
        )
        await select_dropdown(
            page, TERMINATION_REASON_SELECT,
            term.termination_reason,
        )
        await select_dropdown(
            page, TERMINATION_TYPE_SELECT,
            term.termination_type,
        )
        await click_checkbox(
            page, ELIGIBLE_FOR_REHIRE_CHECKBOX,
            term.eligible_for_rehire,
        )

        # Optional: final pay details
        if term.final_pay_date:
            await fill_date_field(
                page, FINAL_PAY_DATE_INPUT,
                term.final_pay_date.strftime("%m/%d/%Y"),
            )
        await click_checkbox(
            page, PAYOUT_PTO_CHECKBOX, term.payout_pto
        )

        if term.notes:
            await fill_text_field(page, NOTES_INPUT, term.notes)

        # Step 4: Review and submit
        await page.click(REVIEW_BUTTON)
        await page.wait_for_selector(
            REVIEW_CONFIRMATION, timeout=10000
        )
        await page.click(SUBMIT_BUTTON)
        await page.wait_for_selector(
            SUCCESS_BANNER, timeout=15000
        )
        return True

    except Exception as e:
        await capture_screenshot(page, "termination_error")
        raise
```

### 7. Selectors

> **CRITICAL**: All selectors below are **placeholders**. You MUST inspect the live ADP pages with browser DevTools to get accurate selectors. ADP uses dynamic IDs and shadow DOM in some areas.

#### Login Selectors (`src/adp/selectors/login.py`)

```python
"""ADP login page selectors."""

USERNAME_INPUT = "#login-form_username"
PASSWORD_INPUT = "#login-form_password"
NEXT_BUTTON = "button[type='submit']"
SIGN_IN_BUTTON = "#verifUserid498"
MFA_INPUT = "#mfaCode"
```

#### New Hire Selectors (`src/adp/selectors/new_hire.py`)

```python
"""ADP new hire form selectors. PLACEHOLDERS — update from DevTools."""

FIRST_NAME_INPUT = "#firstName"
LAST_NAME_INPUT = "#lastName"
SSN_INPUT = "#ssn"
DOB_INPUT = "#dateOfBirth"
EMAIL_INPUT = "#email"
PHONE_INPUT = "#phone"
ADDRESS_LINE_1_INPUT = "#addressLine1"
ADDRESS_LINE_2_INPUT = "#addressLine2"
CITY_INPUT = "#city"
STATE_SELECT = "#state"
ZIP_INPUT = "#zipCode"
JOB_TITLE_INPUT = "#jobTitle"
DEPARTMENT_SELECT = "#department"
PAY_RATE_INPUT = "#payRate"
PAY_FREQUENCY_SELECT = "#payFrequency"
START_DATE_INPUT = "#startDate"
SUBMIT_BUTTON = "button[data-action='submit']"
SUCCESS_BANNER = ".success-notification"
```

#### Termination Selectors (`src/adp/selectors/termination.py`)

```python
"""ADP termination form selectors. PLACEHOLDERS — update from DevTools."""

# Employee search
EMPLOYEE_SEARCH_INPUT = "#employeeSearch"
SEARCH_BUTTON = "button[data-action='search']"
EMPLOYEE_RESULT = ".employee-search-result:first-child"

# Actions menu
ACTIONS_MENU = "#actionsMenu"
TERMINATE_ACTION = "[data-action='terminate']"

# Termination form
TERMINATION_FORM = "#terminationForm"
TERMINATION_DATE_INPUT = "#terminationDate"
LAST_WORK_DATE_INPUT = "#lastWorkDate"
TERMINATION_REASON_SELECT = "#terminationReason"
TERMINATION_TYPE_SELECT = "#terminationType"
ELIGIBLE_FOR_REHIRE_CHECKBOX = "#eligibleForRehire"
FINAL_PAY_DATE_INPUT = "#finalPayDate"
PAYOUT_PTO_CHECKBOX = "#payoutPto"
NOTES_INPUT = "#terminationNotes"

# Review & submit
REVIEW_BUTTON = "button[data-action='review']"
REVIEW_CONFIRMATION = ".review-confirmation"
SUBMIT_BUTTON = "button[data-action='submit']"
SUCCESS_BANNER = ".success-notification"
```

### 8. Screenshot Utility (`src/utils/screenshots.py`)

```python
import os
from datetime import datetime

from playwright.async_api import Page

from src.config import settings


async def capture_screenshot(page: Page, prefix: str) -> str:
    """Capture a debug screenshot on failure.

    Args:
        page: The Playwright page to screenshot.
        prefix: Filename prefix (e.g., 'new_hire_error').

    Returns:
        Path to the saved screenshot.
    """
    os.makedirs(settings.screenshot_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(
        settings.screenshot_dir, f"{prefix}_{timestamp}.png"
    )
    await page.screenshot(path=path, full_page=True)
    return path
```

### 9. Custom Exceptions (`src/adp/exceptions.py`)

```python
class ADPError(Exception):
    """Base exception for ADP automation errors."""

    pass


class LoginError(ADPError):
    """Raised when ADP login fails."""

    pass


class FormSubmissionError(ADPError):
    """Raised when an ADP form submission fails."""

    def __init__(self, message: str, screenshot_path: str | None = None):
        super().__init__(message)
        self.screenshot_path = screenshot_path


class EmployeeNotFoundError(ADPError):
    """Raised when employee search returns no results during termination."""

    pass


class NavigationError(ADPError):
    """Raised when ADP page navigation fails."""

    pass
```

### 10. Error Handling & Reporting

- Wrap all ADP interactions in try/except.
- On failure: capture screenshot via `capture_screenshot()`, log the error, send Telegram message with error summary and screenshot attachment.
- On success: send Telegram confirmation with employee name and action completed.
- Both form modules raise custom exceptions that bubble up to the Telegram handler layer.

---

## Security Considerations

1. **Whitelist Telegram users** — only `TELEGRAM_ALLOWED_USER_IDS` can trigger commands.
2. **Encrypt `.env`** or use a secrets manager (AWS Secrets Manager, HashiCorp Vault) in production.
3. **Never log SSNs, passwords, or other PII** — mask them in logs using `SecretStr`.
4. **Run Playwright in headless mode** in production (`HEADLESS=true`).
5. **Session cleanup** — always close the browser context after each automation run.
6. **Rate limiting** — throttle Telegram commands to prevent accidental rapid-fire submissions.
7. **Audit trail** — log every automation run (who triggered, when, action type, success/fail) to a file or database.
8. **Screenshot security** — debug screenshots may contain sensitive ADP data; store securely and auto-delete after review.

---

## Setup Instructions

```bash
# 1. Clone the repo
git clone <repo-url> && cd hr-pilot

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your Telegram token, ADP credentials, etc.

# 6. Run the bot
python -m src.main
```

---

## `requirements.txt`

```
python-telegram-bot>=20.7
playwright>=1.40.0
pydantic>=2.5.0
python-dotenv>=1.0.0
pyotp>=2.9.0
```

---

## Testing

- **Unit tests**: Test message parsing, model validation, and parsers with pytest.
- **Integration tests**: Use Playwright's `expect` API to validate form filling against a staging environment or mock.
- **Never run integration tests against production ADP.**

```bash
pytest tests/ -v
```

---

## 🚀 Current Implementation Status (Last Updated: 2026-02-15)

### ✅ Completed Components

#### Authentication & Login (`src/adp/auth.py`)
- ✅ **Login flow fully working** with retry logic (3 attempts with exponential backoff)
- ✅ **Popup dismissal implemented** - Automatically dismisses "Remind me later" dialog
- ✅ **Verified selectors**:
  - `USERNAME_INPUT = 'input[autocomplete="username"]'`
  - `PASSWORD_INPUT = 'input[autocomplete="current-password"]'`
  - `NEXT_BUTTON = '#verifUseridBtn'`
  - `SIGN_IN_BUTTON = '#signBtn'`
  - `REMIND_ME_LATER_BUTTON = 'sdf-button[aria-label="Remind me later"]'`
- ✅ Successfully reaches dashboard: `https://workforcenow.adp.com/theme/admin.html#/home`

#### Navigation to New Hire Form (`src/adp/navigation.py`)
- ✅ **Complete navigation flow tested and working**
- ✅ **Verified selectors** in `src/adp/selectors/new_hire.py`:
  - `PROCESS_MENU_BUTTON = 'button:has-text("Process")'` ✅
  - `HIRE_REHIRE_LINK = 'a[href="#/Process/ProcessTabHRCategoryHireRehire"]'` ✅
  - `GO_TO_HIRE_BUTTON = '#navigateToNewHireViewId'` ✅
  - `HR_PR_NEW_HIRES_CARD = 'sdf-box:has-text("HR PR New Hires")'` ✅

#### Configuration (`src/config.py`)
- ✅ Pydantic Settings with proper validation
- ✅ SecretStr for sensitive data
- ✅ User ID whitelist parsing

#### Data Models (`src/models/`)
- ✅ `base.py` - ActionType and ActionStatus enums
- ✅ `termination.py` - Complete with validation
- ✅ `new_hire.py` - Complete with validation

#### Utilities
- ✅ `src/utils/logger.py` - Logging configuration
- ✅ `src/utils/screenshots.py` - Screenshot capture
- ✅ `src/adp/base_form.py` - Form filling utilities
- ✅ `src/adp/exceptions.py` - Custom exception classes

#### Test Infrastructure
- ✅ `tests/test_login_nav.py` - Comprehensive login and navigation test
  - Tests login flow
  - Verifies popup dismissal
  - Tests complete navigation to new hire form
  - Captures screenshots at each step
  - Allows 60s manual inspection
- ✅ `tests/test_form_fill.py` - Full dry-run form fill test
  - Logs in, navigates, fills all form sections, captures Associate ID
  - Dry run confirmed working (form NOT submitted)
  - Associate ID successfully captured

#### New Hire Form (`src/adp/new_hire_form.py`)
- ✅ **Dry run fully working** — all sections fill correctly
- ✅ Personal section: name, phone, email, hire date, reason, company code, tax ID
- ✅ Associate ID captured after tax ID selection
- ✅ Ask the New Hire modal: onboarding experience, worked-in-state, manager, E-Verify location
- ✅ Employment section: job title, worker category, benefits eligibility, measurement periods, home department
- ✅ Payroll section: compensation type, pay rate
- ✅ Tax section: SUI/SDI tax code
- ✅ Direct Deposit section: skipped
- ✅ Emergency Contact section: skipped
- ✅ `dry_run=True` stops before Save and Exit; returns `associate_id`, `screenshot_path`, `warnings`

#### Registration Code Delivery (`src/adp/registration_code.py`)
- ✅ Implemented — navigates to Security Management → Personal Registration Codes
- ✅ Searches by Associate ID, selects employee, sends to personal email
- ⚠️ Not yet tested end-to-end (triggered after /confirm in Telegram flow)

#### Telegram /newhire Flow
- ✅ `/newhire` — parse → validate → dry-run fill → screenshot → wait for /confirm
- ✅ `/confirm` — submit form → send registration code → success message
- ✅ `/cancel` — close browser, discard pending hire
- ✅ Auto-cancel after 5 minutes via job_queue
- ✅ Warnings surfaced to user if manager assignment fails

---

### 🔧 In Progress / Needs Implementation

#### High Priority
1. **Termination Form Automation** (`src/adp/termination_form.py`)
   - File exists but only has TODO comments
   - Need to implement employee search
   - Need to implement termination workflow
   - Selectors in `src/adp/selectors/termination.py` are placeholders

2. **"Did you start this hire already?" popup handling**
   - ADP shows `sdf-focus-pane[id="showInProgressActiveEmpInfo_Id"]` if a prior in-progress hire exists for the same person
   - Need to add dismissal logic at the start of `fill_new_hire_form()`

#### Medium Priority
3. **MFA Support** - Framework exists but no pyotp implementation yet
4. **ConversationHandler** - Currently using simple CommandHandlers
5. **Browser Context Management** - Add proper async context managers

---

### 🔑 Key Learnings & Important Notes

#### Running Tests Properly
- **ALWAYS use virtual environment**: `.venv/Scripts/python.exe tests/test_login_nav.py`
- **NOT**: `python tests/test_login_nav.py` (uses system Python/Anaconda)
- Playwright browsers must be installed: `python -m playwright install chromium`

#### Encoding Issues on Windows
- Avoid emoji characters (✅ ❌) in print statements
- Use `[OK]` and `[FAIL]` instead for Windows cp1252 compatibility
- Affects test scripts and logging output

#### ADP Navigation Timing
- Use 15000ms (15s) initial wait after login before interacting with the dashboard
- Use 30000ms (30s) `wait_for_selector` timeout for the Process menu button (dashboard load is variable)
- Add `wait_for_timeout(3000)` after each section Next button click — ADP renders all sections simultaneously in the DOM; the next section is hidden until the transition completes
- Dashboard load time is inconsistent — navigation may intermittently fail; simply re-run

#### ADP MDFSelectBox Dropdowns
- Most ADP dropdowns use the **MDFSelectBox** React Select pattern — NOT standard `<select>` elements
- Use `fill_mdf_dropdown(page, selector, search_code, match_text)` from `base_form.py`
- Pattern: click → fill short code (no trailing space) → wait 1.5s → click option by `[class*="MDFSelectBox__option"]:has-text("...")`
- `get_search_code(adp_value)` in `config_tables.py` extracts code before " - "; returns first 3 chars if no " - " found
- **Space-sensitive**: "BE " kills results, "BE" works — never include trailing space in search_code
- `page.fill()` does NOT trigger React onChange on these inputs — always use the MDF pattern

#### React Input Fields (Pay Rate)
- `page.fill()` sets DOM value but React's controlled components ignore it (no onChange fired)
- For numeric/text React inputs: `page.click()` → `Control+A` → `page.type()` → `Tab`
- `page.type()` fires native keyboard events that React's synthetic event system picks up

#### Ambiguous "Next" Button Selectors
- ADP keeps Next buttons for ALL form sections in the DOM at once — `button.vdl-button--primary:has-text("Next")` resolves to 5+ elements
- Playwright picks the first by DOM order (often a hidden section's button) and waits forever for it to become visible
- Use `click_visible_next_button(page)` from `base_form.py` — finds the first button where `offsetParent !== null` (visible) via JavaScript

#### Manager Search (Reports To)
- ADP manager search does NOT work with full names — use last name only (or partial last name)
- `LOCATION_MANAGERS` stores `{"name": "Full Name", "search": "LastName"}` — always search by `manager["search"]`
- After search, check for "There are no entries" text before attempting radio button click
- Radio button selector: `sdf-radio-button[role="radio"][aria-checked="false"]` — click first result, verify `aria-checked="true"` after
- If manager search fails: press `Escape` to dismiss the Reports To slider, append to `warnings`, continue — do NOT crash

#### Popup Handling
- "Remind me later" popup may not appear every time — handled with try/except in `auth.py`
- **"Did you start this hire already?"** popup (`sdf-focus-pane[id="showInProgressActiveEmpInfo_Id"]`) appears when ADP detects an in-progress hire for the same person — must be dismissed before filling form fields
- In-progress records from dry runs accumulate — delete them manually from ADP's In-Progress Hires list to prevent this popup

#### Selectors Strategy
- Prefer text-based selectors where stable: `button:has-text("Process")`
- Use ID selectors for form inputs: `#navigateToNewHireViewId`
- Use attribute selectors for links: `a[href="#/Process/ProcessTabHRCategoryHireRehire"]`
- Use shadow DOM selectors for ADP custom elements: `sdf-box:has-text("HR PR New Hires")`

#### Screenshot Debugging
- All navigation screenshots saved to `screenshots/` directory
- Screenshots captured at each navigation step for debugging
- Full page screenshots preferred: `await page.screenshot(path=path, full_page=True)`

---

### 📋 Dependencies Status

**Installed & Working:**
- ✅ `python-telegram-bot>=20.7`
- ✅ `playwright>=1.40.0`
- ✅ `pydantic>=2.5.0`
- ✅ `pydantic-settings>=2.0.0`
- ✅ `python-dotenv>=1.0.0`

**Missing (needed for full implementation):**
- ❌ `pyotp>=2.9.0` - For MFA/TOTP support

---

### 🎯 Next Steps for Implementation

1. **Handle "Did you start this hire already?" popup** in `fill_new_hire_form()`
   - Add try/except at the start of the form fill to detect and dismiss `sdf-focus-pane[id="showInProgressActiveEmpInfo_Id"]`

2. **End-to-end test with real data**
   - Run `tests/test_form_fill.py` with `dry_run=False` on a test employee
   - Verify Associate ID is captured correctly
   - Verify registration code is delivered to personal email

3. **Implement Termination Workflow**
   - Complete `fill_termination_form()` in `src/adp/termination_form.py`
   - Verify/update selectors in `src/adp/selectors/termination.py`
   - Wire `/terminate` handler to termination automation

4. **End-to-end Telegram test**
   - Send `/newhire` message via Telegram with real employee data
   - Verify dry-run screenshot is received, /confirm submits correctly
   - Verify registration code delivery

---

## Common Issues & Troubleshooting

| Issue | Solution |
|---|---|
| ADP selectors broken | Inspect ADP page with DevTools, update the relevant file in `selectors/` |
| MFA prompt blocking login | Ensure `ADP_MFA_SECRET` is set; implement TOTP handling in `auth.py` |
| Playwright times out | Increase timeout (15000ms for ADP), check network/VPN connectivity |
| Playwright browsers not installed | Run `python -m playwright install chromium` in virtual environment |
| Using wrong Python interpreter | Always use `.venv/Scripts/python.exe` not system `python` |
| Unicode encoding errors on Windows | Avoid emoji in print statements, use `[OK]`/`[FAIL]` instead of ✅/❌ |
| Telegram bot not responding | Verify token, check webhook vs polling mode, check firewall |
| Rate limited by ADP | Add delays between interactions (`page.wait_for_timeout(1000)`) |
| Employee not found (termination) | Verify employee ID format matches ADP's expected format |
| Termination form has extra steps | Some ADP configs require benefits termination — update `termination_form.py` |
| Navigation fails intermittently | ADP dashboard load is variable; re-run the test. Use 15s initial wait + 30s selector timeout |
| Dropdown not selecting (MDFSelectBox) | Use `fill_mdf_dropdown()` not `fill_react_dropdown()`. No trailing space in search_code |
| Pay rate field not filling | Use `page.click()` + `Ctrl+A` + `page.type()` + `Tab` — `page.fill()` doesn't fire React onChange |
| "Next" button click does nothing | Use `click_visible_next_button()` — generic `button:has-text("Next")` matches hidden buttons from other sections |
| Section field not visible after Next | Add `wait_for_timeout(3000)` after clicking Next — ADP keeps all sections in DOM, transition takes time |
| Manager search returns no entries | Use last name only (`manager["search"]`), not full name. ADP search rejects full names |
| Reports To slider blocks subsequent clicks | If manager search fails, press `Escape` to close the slider before continuing |
| "Did you start this hire already?" popup | Delete the in-progress record from ADP's In-Progress Hires list, or add popup dismissal code |

---

## Future Enhancements

- **Conversation flows**: Use `ConversationHandler` for guided multi-step input with per-field validation and correction.
- **CSV bulk upload**: Accept a CSV file via Telegram to process multiple new hires or terminations.
- **Pay changes**: Add `/paychange` workflow for salary/rate adjustments.
- **Department transfers**: Add `/transfer` workflow for moving employees between departments.
- **Scheduling**: Queue submissions for off-peak hours via Celery + Redis.
- **Dashboard**: Simple web dashboard to view automation run history and audit logs.
- **ADP API integration**: If ADP API access becomes available, replace browser automation with direct API calls for reliability.
- **Status tracking**: `/status` command to check the result of a previously submitted action.
