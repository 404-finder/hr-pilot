# CLAUDE.md — hr-pilot: Telegram-to-ADP HR Automation

## User Interaction
- Be concise and professional in your responses
- Present code first then explain your code
- Ask clarifying questions when you are unsure
- Favor readability over fancy solutions
- Print statements in code are short yet informative

## Project Overview

Build a Python automation system called **hr-pilot** that:

1. **Receives Telegram messages** containing HR action requests via a Telegram Bot.
2. **Parses messages** into structured data using Pydantic models.
3. **Logs into ADP Workforce Now** using browser automation.
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
| Settings | `pydantic-settings` | Load `.env` into typed settings object |
| Logging | `logging` (stdlib) | Structured logging throughout |

---

## Project Structure

```
hr-pilot/
├── CLAUDE.md                      # This file
├── ADP_SELECTORS_REFERENCE.md     # Complete ADP selector documentation
├── .env                           # Secrets (DO NOT COMMIT)
├── .env.example                   # Template for .env
├── .gitignore
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point — starts Telegram bot
│   ├── config.py                  # Pydantic Settings loader from .env
│   ├── config_tables.py           # ADP dropdown mappings & validation lookups
│   ├── validators.py              # Input validation against config_tables
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # ActionType and ActionStatus enums
│   │   ├── new_hire.py            # NewHire Pydantic model
│   │   └── termination.py         # Termination Pydantic model
│   ├── telegram_bot/
│   │   ├── __init__.py
│   │   ├── bot.py                 # Bot setup, handler registration
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── common.py          # /start, /help, /cancel, error handler
│   │   │   ├── new_hire.py        # /newhire + /confirm + /cancel flow
│   │   │   └── termination.py     # /terminate handler (not yet implemented)
│   │   └── parsers.py             # Parse telegram messages → dicts → models
│   ├── adp/
│   │   ├── __init__.py
│   │   ├── auth.py                # ADP login with retry logic
│   │   ├── base_form.py           # Shared form utilities (MDF dropdowns, etc.)
│   │   ├── navigation.py          # Navigate ADP menus and pages
│   │   ├── new_hire_form.py       # New hire form automation
│   │   ├── registration_code.py   # Send PRC via Security Management
│   │   ├── termination_form.py    # Termination form (TODO)
│   │   ├── exceptions.py          # Custom exception classes
│   │   └── selectors/
│   │       ├── __init__.py
│   │       ├── login.py           # Login page selectors (verified)
│   │       ├── new_hire.py        # New hire form selectors (verified)
│   │       └── termination.py     # Termination selectors (placeholders)
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging config (console + rotating file)
│       └── screenshots.py         # Debug screenshot capture
├── tests/
│   ├── __init__.py
│   ├── test_login_nav.py          # Login + navigation test
│   └── test_form_fill.py          # Full dry-run form fill test
└── screenshots/                   # Debug screenshots (gitignored)
```

---

## Environment Variables (`.env`)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# ADP Credentials
ADP_USERNAME=your-adp-username
ADP_PASSWORD=your-adp-password

# App Settings
LOG_LEVEL=INFO
HEADLESS=true
SCREENSHOT_DIR=screenshots
```

---

## Coding Standards

- Follow **PEP 8** strictly.
- Use **type hints** on all function signatures and return types.
- Use **`async`/`await`** throughout — `python-telegram-bot` v20+ and Playwright async API.
- All sensitive data (passwords, SSNs) must be handled securely:
  - Never log sensitive fields.
  - Use `pydantic.SecretStr` for passwords and SSNs in models.
  - Clear browser session data after each automation run.
- Write **docstrings** for all public functions and classes (Google style).
- Keep functions small and single-purpose.
- Use `logging` module — never `print()` (except in test scripts).
- Constants in `UPPER_SNAKE_CASE`, classes in `PascalCase`, functions/variables in `snake_case`.
- All packages must be installed in the virtual environment `.venv`.

---

## `requirements.txt`

```
python-telegram-bot>=20.7
playwright>=1.40.0
pydantic>=2.5.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

---

## Telegram Message Format

### `/newhire` Command

```
/newhire
First Name: John
Last Name: Doe
Email: john.doe@company.com
Phone: 555-123-4567
Store Number: 39104
Job Title: Crew
Work Schedule: Part Time
Pay Rate: 15.50
Pay Type: hourly
Start Date: 03/01/2026
Reason: New Hire
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

### Field Options (New Hire)

| Field | Valid Options |
|---|---|
| Store Number | 39101 (Hewitt Drive), 39102 (Interstate 35), 39103 (South Valley Mills), 39104 (North Valley Mills) |
| Job Title | assist manager, co-manager, crew, dist manager, gen manager, manager, sal manager |
| Work Schedule | full time, part time |
| Pay Type | hourly, salary |
| Reason | current, new hire (defaults to "new hire") |

All field names and values are **case-insensitive**.

---

## Data Models (Actual Implementation)

### `NewHire` (`src/models/new_hire.py`)

```python
class NewHire(BaseModel):
    # Required fields from Telegram
    first_name: str
    last_name: str
    email: str
    phone: str
    store_number: str          # Validated against STORE_LOCATIONS
    job_title: str             # Validated against JOB_TITLES (case-insensitive)
    work_schedule: str         # Validated against WORK_SCHEDULE (case-insensitive)
    pay_rate: float
    pay_frequency: str         # "hourly" | "salary"
    start_date: date
    reason: str = "new hire"   # Validated against REASON_FOR_HIRE

    # Optional (delegated to new hire via ADP "Ask the New Hire" flow)
    ssn: Optional[SecretStr] = None
    date_of_birth: Optional[date] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
```

**Key design decisions:**
- Manager is auto-derived from `store_number` via `config_tables.LOCATION_MANAGERS`
- Home department is auto-derived from `store_number` + `job_title` via `config_tables.get_home_department()`
- SSN, DOB, and address are delegated to the new hire (filled via ADP's onboarding flow)

---

## Config Tables (`src/config_tables.py`)

Central lookup module that maps user-friendly input to ADP dropdown values.

### Dropdown Mappings

| Table | Example Input → ADP Value |
|---|---|
| `REASON_FOR_HIRE` | "new hire" → "NEW - New Position" |
| `JOB_TITLES` | "crew" → "TEAMMEMB - TEAM MEMBER" |
| `WORK_SCHEDULE` | "part time" → "RPT - REGULAR PART TIME" |
| `STORE_LOCATIONS` | "39104" → "North Valley Mills" |
| `LOCATION_MANAGERS` | "39104" → `{"name": "Mary De Los Rios", "search": "De Los Rios"}` |
| `TAX_ID_TYPE` | "ssn" → "United States Social Security Number (SSN)" |

### Store Config (prefix-based)

```python
STORE_CONFIG = {
    "3910": {
        "company_code": "ZKT - LC Texas LLC",
        "worked_in_state": "TX - Texas",
        "sui_sdi_tax_code": "TX -53 -Texas",
        "onboarding_experience": "Texas Experience LC Texas",
        "benefits_eligibility": "BE - Benefit Eligible Team Members",
        "measurement_periods": True,
    }
}
```

Store number "39104" matches prefix "3910" → returns the config dict.

### Helper Functions

| Function | Purpose |
|---|---|
| `get_search_code(adp_value)` | Extract code before " - " for MDF dropdown search (e.g., "BE - ..." → "BE") |
| `get_store_config(store_number)` | Look up STORE_CONFIG by prefix |
| `get_home_department(store_number, job_title_key)` | Build dept code: store + suffix ("0" for managers, "3" for crew) |
| `get_everify_location(store_number)` | Look up store name from STORE_LOCATIONS |
| `get_manager(store_number)` | Returns `{"name": "Full Name", "search": "LastName"}` dict |

---

## ADP Automation Architecture

### Login Flow (`src/adp/auth.py`)

`login_to_adp()` → returns `(Browser, Page)` tuple.

- Retry logic: 3 attempts with exponential backoff (2s, 4s, 8s)
- Popup dismissal: "Remind me later" dialog handled with try/except
- Raises `LoginError` after all retries exhausted

### Verified Login Selectors (`src/adp/selectors/login.py`)

```python
USERNAME_INPUT = 'input[autocomplete="username"]'
PASSWORD_INPUT = 'input[autocomplete="current-password"]'
NEXT_BUTTON = '#verifUseridBtn'
SIGN_IN_BUTTON = '#signBtn'
REMIND_ME_LATER_BUTTON = 'sdf-button[aria-label="Remind me later"]'
```

### Navigation (`src/adp/navigation.py`)

| Function | Path |
|---|---|
| `navigate_to_new_hire(page)` | Process → Hire/Rehire → Go to Hire → HR PR New Hires |
| `navigate_to_security_management(page)` | Setup → Security Management |
| `navigate_to_registration_codes(page)` | People (hover) → Personal Registration Codes |

### Base Form Utilities (`src/adp/base_form.py`)

| Function | Purpose |
|---|---|
| `fill_text_field(page, selector, value)` | Clear and fill text input |
| `fill_date_field(page, selector, date_str)` | Fill date picker + Tab to validate |
| `click_checkbox(page, selector, should_check)` | Toggle checkbox state |
| `select_dropdown(page, selector, value)` | Native `<select>` dropdown |
| `fill_mdf_dropdown(page, selector, search_code, match_text)` | **ADP MDFSelectBox React Select** — type short code, wait, click matching option |
| `fill_react_dropdown(page, selector, value)` | Generic React Select (click, type, Enter) |
| `click_and_wait(page, click_selector, wait_selector)` | Click then wait for next element |
| `click_visible_next_button(page)` | Find and click the first *visible* Next button via JS evaluation |

### New Hire Form (`src/adp/new_hire_form.py`)

`fill_new_hire_form(page, hire, dry_run=True)` → returns dict:
```python
{
    "associate_id": str,      # Captured from form
    "screenshot_path": str,   # Review screenshot
    "submitted": bool,        # False if dry_run=True
    "warnings": list[str],    # e.g., manager search issues
}
```

**Form sections filled in order:**

1. **Personal Section** — name, phone, email, notification checkbox, hire date, reason, company code, tax ID type, capture Associate ID
2. **Ask the New Hire Modal** — onboarding experience, worked-in state, manager (Reports To), E-Verify location
3. **Employment Section** — job title, worker category, benefits eligibility, measurement periods, home department
4. **Payroll Section** — compensation type (Hourly), pay rate
5. **Tax Section** — SUI/SDI tax code
6. **Direct Deposit** — skipped
7. **Emergency Contact** — skipped
8. **Dry run check** — screenshot, then Save & Exit only if `dry_run=False`

### Telegram Flow

1. User sends `/newhire` message
2. `parse_new_hire_raw()` → raw dict
3. `validate_new_hire_input()` → check against config_tables, return errors if invalid
4. `parse_new_hire()` → create `NewHire` model
5. Login to ADP → navigate → `fill_new_hire_form(dry_run=True)`
6. Send screenshot to user for review
7. User sends `/confirm` → click Save & Exit → `send_registration_code()` → done
8. Or `/cancel` → close browser, discard
9. Auto-cancel after 5 minutes via `job_queue`

---

## 🚀 Current Implementation Status (Last Updated: 2026-02-25)

### ✅ Completed Components

| Component | Status | Notes |
|---|---|---|
| `src/config.py` | ✅ Working | Pydantic Settings, SecretStr, user ID whitelist |
| `src/config_tables.py` | ✅ Working | All dropdown mappings, helper functions, `get_search_code()` |
| `src/validators.py` | ✅ Working | Case-insensitive validation with friendly error messages |
| `src/models/new_hire.py` | ✅ Working | Field validators for store, job title, work schedule |
| `src/models/termination.py` | ✅ Working | Complete with validation |
| `src/models/base.py` | ✅ Working | ActionType, ActionStatus enums |
| `src/adp/auth.py` | ✅ Working | Login with retry, popup dismissal |
| `src/adp/navigation.py` | ✅ Working | New hire, security management, registration codes |
| `src/adp/base_form.py` | ✅ Working | `fill_mdf_dropdown`, `click_visible_next_button`, etc. |
| `src/adp/new_hire_form.py` | ⚠️ Mostly working | Dry run fills form; some dropdowns may need fixes (see bugs below) |
| `src/adp/registration_code.py` | ✅ Implemented | Not yet tested end-to-end |
| `src/adp/exceptions.py` | ✅ Working | LoginError, FormSubmissionError, NavigationError, etc. |
| `src/adp/selectors/login.py` | ✅ Verified | Real selectors from ADP |
| `src/adp/selectors/new_hire.py` | ✅ Verified | Real selectors from ADP (all sections + PRC) |
| `src/adp/selectors/termination.py` | ❌ Placeholders | TODO |
| `src/telegram_bot/bot.py` | ✅ Working | Registers all handlers |
| `src/telegram_bot/parsers.py` | ✅ Working | Case-insensitive parsing, raw dict + model creation |
| `src/telegram_bot/handlers/common.py` | ✅ Working | /start, /help, /cancel, error handler |
| `src/telegram_bot/handlers/new_hire.py` | ✅ Working | Dry-run → /confirm → submit + PRC flow |
| `src/telegram_bot/handlers/termination.py` | ❌ Stub | "Not yet implemented" message |
| `src/utils/logger.py` | ✅ Working | Console + rotating file handler |
| `src/utils/screenshots.py` | ✅ Working | Timestamped screenshot capture |
| `tests/test_login_nav.py` | ✅ Working | Login + full navigation test |
| `tests/test_form_fill.py` | ✅ Working | Full dry-run test with test data |

### 🔧 Known Bugs / In Progress

1. **"Use for Notification" checkbox** — may not be checking properly; currently uses JS `dispatchEvent` workaround
2. **Employment/Payroll dropdowns may appear empty after run** — Job Title, Worker Category, Benefits Eligibility, Home Department, Compensation Type, Pay Rate may not persist without Save & Exit; needs verification after save
3. **"Did you start this hire already?" popup** — ADP shows `#showInProgressActiveEmpInfo_Id` if prior in-progress hire exists; needs dismissal logic at start of `fill_new_hire_form()`
4. **MFA** — ADP may intermittently require SMS MFA on fresh browser sessions; not yet handled in script

### 🎯 Next Steps

1. Fix remaining dropdown/field persistence bugs (verify after Save & Exit)
2. Handle "Did you start this hire already?" popup
3. Live submit test (`dry_run=False`) with real data
4. End-to-end Telegram test
5. Implement termination workflow
6. Add MFA handling (SMS code input)

---

## 🔑 Key Learnings & Critical Notes

### Running Tests
- **ALWAYS use virtual environment**: `.venv/Scripts/python.exe tests/test_form_fill.py`
- **NOT**: `python tests/test_form_fill.py` (may use system Python/Anaconda)
- Playwright browsers must be installed: `python -m playwright install chromium`

### Encoding Issues on Windows
- Avoid emoji characters in print statements
- Use `[OK]` and `[FAIL]` instead for Windows cp1252 compatibility

### ADP Navigation Timing
- Use 15000ms (15s) initial wait after login before interacting with the dashboard
- Use 30000ms (30s) `wait_for_selector` timeout for the Process menu button
- Add `wait_for_timeout(3000)` after each section Next button click — ADP renders all sections simultaneously in the DOM; the next section is hidden until the transition completes
- Dashboard load time is inconsistent — navigation may intermittently fail; re-run

### ADP MDFSelectBox Dropdowns (CRITICAL)
- Most ADP dropdowns use **MDFSelectBox** React Select — NOT standard `<select>` elements
- Use `fill_mdf_dropdown(page, selector, search_code, match_text)` from `base_form.py`
- Pattern: click → fill short code (no trailing space) → wait 1.5s → click option by `[class*="MDFSelectBox__option"]:has-text("...")`
- `get_search_code(adp_value)` extracts code before " - "; returns first 3 chars if no " - " found
- **Space-sensitive**: "BE " kills results, "BE" works — never include trailing space in search_code
- `page.fill()` does NOT trigger React onChange — always use the MDF pattern

### React Input Fields (Pay Rate)
- `page.fill()` sets DOM value but React's controlled components ignore it (no onChange fired)
- For numeric/text React inputs: `page.click()` → `Control+A` → `page.type()` → `Tab`
- `page.type()` fires native keyboard events that React's synthetic event system picks up

### Ambiguous "Next" Button Selectors
- ADP keeps Next buttons for ALL form sections in the DOM at once
- `button.vdl-button--primary:has-text("Next")` resolves to 5+ elements
- Use `click_visible_next_button(page)` — finds the first visible button via JavaScript `offsetParent !== null`

### Manager Search (Reports To)
- ADP manager search does NOT work with full names — use last name only
- `LOCATION_MANAGERS` stores `{"name": "Full Name", "search": "LastName"}` — always search by `manager["search"]`
- After search, check for "There are no entries" text before attempting radio button click
- Radio button selector: `sdf-radio-button[role="radio"][aria-checked="false"]` — click first result, verify `aria-checked="true"` after
- If manager search fails: press `Escape` to dismiss the slider, append to `warnings`, continue — do NOT crash

### Popup Handling
- **"Remind me later"** popup may not appear every time — handled with try/except in `auth.py`
- **"Did you start this hire already?"** popup (`#showInProgressActiveEmpInfo_Id`) appears when ADP detects an in-progress hire — must be dismissed before filling form fields
- In-progress records from dry runs accumulate — delete them manually from ADP's In-Progress Hires list

### ADP Sticky Toolbar / Viewport Issues
- ADP has a sticky bottom toolbar that can overlay form elements
- `page.check()`, `page.click()`, and even `force=True` may fail when elements are behind this toolbar
- **Solution**: `page.locator(selector).evaluate("el => el.click()")`
- This fires a real DOM click event that React picks up, without needing viewport coordinates
- Use this pattern for any element that reports "outside of the viewport"
- Note: manually setting `.checked = true` + `dispatchEvent('change')` does NOT work — React ignores it. The native `.click()` fires a proper MouseEvent that React's synthetic event system intercepts.

### Selectors Strategy
- Prefer text-based selectors where stable: `button:has-text("Process")`
- Use ID selectors for form inputs: `#navigateToNewHireViewId`
- Use attribute selectors for links: `a[href="#/Process/..."]`
- Use shadow DOM selectors for ADP custom elements: `sdf-box:has-text("HR PR New Hires")`

---

## Common Issues & Troubleshooting

| Issue | Solution |
|---|---|
| ADP selectors broken | Inspect ADP page with DevTools, update `selectors/` |
| Playwright times out | Increase timeout, check network/VPN connectivity |
| Playwright browsers not installed | `python -m playwright install chromium` in venv |
| Using wrong Python interpreter | Always use `.venv/Scripts/python.exe` |
| Unicode encoding errors (Windows) | Use `[OK]`/`[FAIL]` instead of emoji |
| Telegram bot not responding | Verify token, check webhook vs polling mode |
| Rate limited by ADP | Add delays (`page.wait_for_timeout(1000)`) |
| Navigation fails intermittently | ADP dashboard load is variable; re-run |
| Dropdown not selecting (MDFSelectBox) | Use `fill_mdf_dropdown()`. No trailing space in search_code |
| Pay rate field not filling | Use `page.click()` + `Ctrl+A` + `page.type()` + `Tab` |
| "Next" button click does nothing | Use `click_visible_next_button()` |
| Section field not visible after Next | Add `wait_for_timeout(3000)` after clicking Next |
| Manager search returns no entries | Use last name only (`manager["search"]`), not full name |
| Reports To slider blocks clicks | Press `Escape` to close slider if search fails |
| "Did you start this hire already?" popup | Delete in-progress record from ADP, or add dismissal code |
| MFA prompt blocking login | Complete MFA manually; will need script handling for production |

---

## Future Enhancements

- **MFA handling**: SMS code input via terminal (testing) or Telegram (production)
- **"Did you start this hire already?" popup**: Auto-dismiss at start of form fill
- **Dry run cleanup**: Click Cancel after dry run to prevent in-progress record accumulation
- **ConversationHandler**: Replace simple CommandHandlers with guided multi-step input
- **Termination workflow**: Complete `termination_form.py` with real selectors
- **CSV bulk upload**: Accept CSV via Telegram for batch processing
- **Pay changes / transfers**: `/paychange` and `/transfer` workflows
- **Browser context persistence**: Save cookies to avoid MFA on subsequent runs
- **Scheduling**: Queue submissions for off-peak hours
- **Audit trail**: Log all automation runs to file or database
- **ADP API integration**: Replace browser automation if API access becomes available