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
TELEGRAM_ALLOWED_USER_IDS=USER_ID_1,USER_ID_2

# ADP Credentials — one set per Telegram user (increment number for each user)
ADP_USERNAME_1=username1
ADP_PASSWORD_1=password1
TELEGRAM_USER_ID_1=USER_ID_1

ADP_USERNAME_2=username2
ADP_PASSWORD_2=password2
TELEGRAM_USER_ID_2=USER_ID_2

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
python-telegram-bot[job-queue]>=20.7
playwright>=1.40.0
pydantic>=2.5.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

> **Note:** The `[job-queue]` extra installs `APScheduler`, required for auto-cancel timers (`job_queue.run_once()` in handlers).

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
| Store Number | **Texas:** 39101 (Hewitt Drive), 39102 (Interstate 35), 39103 (South Valley Mills), 39104 (North Valley Mills) — **Colorado:** 33561 (Austin Bluffs Pkwy), 33562 (Galley Rd), 33563 (Constitution Ave), 33564 (Cheyenne Meadows Rd), 33565 (Mesa Ridge Pkwy), 33566 (South Academy Blvd), 33567 (Stetson Hills Blvd) |
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
    "3910": {  # Texas stores
        "company_code": "ZKT - LC Texas LLC",
        "worked_in_state": "TX - Texas",
        "sui_sdi_tax_code": "TX -53 -Texas",
        "onboarding_experience": "Texas Experience LC Texas",
        "benefits_eligibility": "BE - Benefit Eligible Team Members",
        "measurement_periods": True,
    },
    "3356": {  # Colorado stores
        "company_code": "FND - LC CO LLC",
        "worked_in_state": "CO - Colorado",
        "sui_sdi_tax_code": "CO -15 - Colorado",
        "onboarding_experience": "Colorado Experience LC CO",
        "benefits_eligibility": "BE - Benefit Eligible Team Members",
        "measurement_periods": True,
    },
}
```

Store number "39104" matches prefix "3910" → returns the Texas config dict.
Store number "33561" matches prefix "3356" → returns the Colorado config dict.

**Colorado store managers:** all 7 stores (33561–33567) map to `{"name": "Caleb Urrutia", "search": "Urrutia"}`.

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

`login_to_adp(username, password)` → returns `(Browser, Page, bool)` tuple.

- Third return value = `mfa_required`: `True` if ADP presented MFA challenge, `False` if login completed normally
- Accepts explicit `username: str` and `password: str` — does not read from settings directly
- Credentials are routed per Telegram user via `settings.get_adp_credentials(telegram_user_id)` in the handler before calling this function
- Retry logic: 3 attempts with exponential backoff (2s, 4s, 8s)
- Comprehensive headless stealth via `context.add_init_script(STEALTH_JS)` — persists across all navigations
- MFA detection: checks for `h1:has-text('Verify Your Identity')` after sign-in; if found, clicks "Send me a text message" and returns `mfa_required=True` with the page on the code entry screen
- Popup dismissal: "Remind me later" dialog + Pendo overlay handled after login
- Dashboard URL check: `https://workforcenow.adp.com/**` (NOT `**/workforcenow.adp.com/**` — see Dashboard URL Check Bug)
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
| `dismiss_pendo(page)` | Dismiss Pendo product-tour overlays that block clicks (close button or JS removal) |

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
5. Login to ADP → if `mfa_required`: prompt user for code via Telegram → user replies → submit code → continue
6. Navigate → `fill_new_hire_form(dry_run=True)`
7. Send screenshot to user for review
8. User sends `/confirm` → click Save & Exit → `send_registration_code()` → done
9. Or `/cancel` → close browser, discard
10. Auto-cancel after 5 minutes via `job_queue` (3 minutes for MFA timeout)

### MFA Flow (`src/telegram_bot/handlers/new_hire.py`)

When ADP requires identity verification during login:

1. `login_to_adp()` detects MFA page (`h1:has-text('Verify Your Identity')`)
2. Clicks "Send me a text message", captures `screenshots/mfa_code_entry.png`, returns `mfa_required=True`
3. Handler stores `browser`, `page`, `hire` in `context.user_data`, sets `awaiting_mfa_code=True`
4. Sends Telegram prompt: "Please reply with the verification code."
5. `handle_mfa_code()` (`MessageHandler` for plain text) receives code, fills `page.get_by_label("Passcode")`, clicks Submit
6. After dashboard redirect, continues with `_run_new_hire_flow()` (navigate → fill → confirm)
7. `auto_cancel_mfa()` fires after 3 minutes if no code received

**Key:** MFA and form-fill errors are in separate `try/except` blocks so error messages are accurate.

### Error Screenshots

- **On error:** Both `handle_new_hire` and post-MFA error handlers auto-send the latest screenshot from `screenshots/` to Telegram
- **On demand:** `/debug` command sends the 3 most recent screenshots
- **Review screenshot:** Captured at the end of form fill for user confirmation before `/confirm`

---

## 🚀 Current Implementation Status (Last Updated: 2026-03-22)

### ✅ Completed Components

| Component | Status | Notes |
|---|---|---|
| `src/config.py` | ✅ Working | Multi-user ADP credentials via numbered env vars; `get_adp_credentials(user_id)` |
| `src/config_tables.py` | ✅ Working | Texas (3910x) + Colorado (3356x) stores, all dropdown mappings, helper functions |
| `src/validators.py` | ✅ Working | Case-insensitive validation with friendly error messages |
| `src/models/new_hire.py` | ✅ Working | Field validators for store, job title, work schedule |
| `src/models/termination.py` | ✅ Working | Complete with validation |
| `src/models/base.py` | ✅ Working | ActionType, ActionStatus enums |
| `src/adp/auth.py` | ✅ Working | Login with retry, popup dismissal, stealth via `add_init_script`, MFA detection + SMS relay |
| `src/adp/navigation.py` | ✅ Working | New hire, security management, registration codes; retry + diagnostics for Process button; Pendo dismissal |
| `src/adp/base_form.py` | ✅ Working | `fill_mdf_dropdown`, `click_visible_next_button`, `dismiss_pendo`; all default timeouts 20s |
| `src/adp/new_hire_form.py` | ✅ Working | Full form fill + Save & Exit tested end-to-end; custom onboarding dropdown handling |
| `src/adp/registration_code.py` | ✅ Working | Tested end-to-end — registration code email delivered successfully |
| `src/adp/exceptions.py` | ✅ Working | LoginError, FormSubmissionError, NavigationError, etc. |
| `src/adp/selectors/login.py` | ✅ Verified | Real selectors from ADP |
| `src/adp/selectors/new_hire.py` | ✅ Verified | Real selectors from ADP (all sections + PRC) |
| `src/adp/selectors/termination.py` | ❌ Placeholders | TODO |
| `src/telegram_bot/bot.py` | ✅ Working | Registers all handlers including MFA `MessageHandler` and `/debug` |
| `src/telegram_bot/parsers.py` | ✅ Working | Case-insensitive parsing, raw dict + model creation |
| `src/telegram_bot/handlers/common.py` | ✅ Working | /start, /help, /cancel, /debug, error handler |
| `src/telegram_bot/handlers/new_hire.py` | ✅ Working | Dry-run → /confirm → submit + PRC flow; MFA code relay; auto-send screenshots on error |
| `src/telegram_bot/handlers/termination.py` | ❌ Stub | "Not yet implemented" message |
| `src/utils/logger.py` | ✅ Working | Console + rotating file handler; used via `setup_logger(__name__)` |
| `src/utils/screenshots.py` | ✅ Working | Viewport screenshot capture (not full_page) with 60s timeout |
| `tests/test_login_nav.py` | ✅ Working | Login + full navigation test |
| `tests/test_form_fill.py` | ✅ Working | Full dry-run test with test data |

### ✅ Completed Features

| Feature | Notes |
|---|---|
| MFA handling | Auto-detect, SMS trigger, Telegram relay, code entry — works from VPS |
| Colorado stores (33561-33567) | All 7 stores configured; manager = Caleb Urrutia |
| Multi-user ADP credentials | Per-user via numbered env vars; routed by Telegram user ID |
| VPS deployment with systemd | DigitalOcean SFO3, Ubuntu 24.04, user `big-al`, `hr-pilot.service` |
| Headless Chromium stealth | `STEALTH_JS` via `context.add_init_script()` — 6 detection vectors covered |
| Logging with setup_logger() | All `src/adp/` modules use `setup_logger(__name__)` — outputs to console + file |

### 🔧 Known Bugs / In Progress

1. **"Did you start this hire already?" popup** — ADP shows `#showInProgressActiveEmpInfo_Id` if prior in-progress hire exists; needs dismissal logic at start of `fill_new_hire_form()`

### 🎯 Next Steps

1. Handle "Did you start this hire already?" popup
2. Implement termination workflow
3. Dry run cleanup (cancel form to prevent in-progress accumulation)
4. Browser session persistence (save cookies to skip MFA on subsequent runs)

---

## 🔑 Key Learnings & Critical Notes

### Logging (CRITICAL)
- All `src/adp/` modules MUST use `from src.utils.logger import setup_logger` then `logger = setup_logger(__name__)`
- Do NOT use `logging.getLogger(__name__)` — it creates a logger with no handlers, so all log output is silently dropped (invisible in `journalctl`)
- `setup_logger()` adds console handler + rotating file handler (`logs/hr_pilot.log`) with `asctime | name | level | message` format

### __pycache__ on VPS (CRITICAL)
- After every `git pull` on VPS, clear `__pycache__`: `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null`
- Stale `.pyc` bytecode files cause Python to use old code even after pulling new source files
- Symptom: changes don't take effect after deploy, old behavior persists

### Running Tests
- **ALWAYS use virtual environment**: `.venv/Scripts/python.exe tests/test_form_fill.py`
- **NOT**: `python tests/test_form_fill.py` (may use system Python/Anaconda)
- Playwright browsers must be installed: `python -m playwright install chromium`

### Encoding Issues on Windows
- Avoid emoji characters in print statements
- Use `[OK]` and `[FAIL]` instead for Windows cp1252 compatibility

### ADP Navigation Timing
- Dashboard wait: `wait_for_load_state("domcontentloaded")` + 15s static buffer (replaces old 30s static-only wait)
- Process menu button: 60s timeout, with automatic retry (screenshot + page reload + 15s + 60s retry) via `_wait_for_process_button()`
- All subsequent nav selectors: 20s timeout (Hire/Rehire, Go to Hire, New Hires card, Setup, Security Management, People, PRC, search form)
- New tab detection timeout: 10s; new tab load state: 60s
- Add `wait_for_timeout(3000)` after each section Next button click — ADP renders all sections simultaneously in the DOM; the next section is hidden until the transition completes
- Form interactivity wait: 5s static before first field fill (VPS fields can be visible but not interactive)
- First field (`#Name\.first`) timeout: 30s (ADP may re-render form DOM after initial visibility)
- Company Code → Tax ID Type: 2s settle wait after company code, 20s timeout for Tax ID Type
- Spinner wait: up to 15s before "Ask the New Hire" modal for ADP async re-renders to complete
- **All form `wait_for_selector` timeouts: 20s minimum** — VPS is consistently slower; elements resolve as visible in Playwright but React components need more time to become interactive. All `base_form.py` utility function defaults set to 20000ms (2026-03-22).
- Dashboard load time is inconsistent — navigation may intermittently fail; re-run

### Reports To Slider Animation (VPS — Fixed 2026-03-16)
- Clicking `#openReportsToCustomSlider_Id` opens the "Change Reports To" slider panel
- On VPS, the slider animation takes several seconds — `#onReportsToSearch` resolves as visible in Playwright's call log but the `wait_for_selector` still times out (element flickers during animation/re-render)
- **Fix**: add `wait_for_timeout(3000)` after clicking the Reports To button, before waiting for the search input
- The error screenshot (captured in the `except` block seconds later) shows the panel fully loaded — confirming the element IS there, just not stable within the original timeout window

### Onboarding Experience Pencil Icon (CRITICAL — Fixed 2026-03-22)
- The pencil/edit icon is `SDF-BUTTON#assignedTemplateName_Id` — a 14x16px Font Awesome icon (`fa fa-pencil`) next to "None" text
- **Two "Assign onboarding experience" elements exist in the DOM**: one in the header (`#ENHAssignOnboarding` at y=-657, above viewport) and one in the visible modal content. On VPS, both can have zero dimensions if the modal isn't scrolled into view
- **Pre-scroll fix**: Before the pencil click, scroll `#ENHAskNewhire` / `[class*="askNewHire"]` / `[class*="prehire"]` into view, then scroll `text=Assign onboarding experience` into view, then wait 1s
- **Fix**: JS `page.evaluate()` with `isVisible()` filter (`r.top >= -100 && r.top < window.innerHeight`) skips the off-screen duplicate. Wrapped in `asyncio.wait_for(timeout=15)` to prevent hanging
- Strategy A: click visible parent button/link of the label. Strategy B: walk up 2-3 levels to find a visible sibling (the pencil icon)

### Onboarding Experience Dropdown (CRITICAL — Fixed 2026-03-22)
- The dropdown inside the sub-page slide-in (`#showTemplateSlideIn_Id`) is an **MDFSelectBox** (`#onboardingTemplateId`), but the input element is **hidden** — Playwright can't click it directly
- `fill_mdf_dropdown()` does NOT work for this dropdown (works for all others)
- **Fix**: Custom interaction sequence — force-click hidden input, dispatch `focus` + `mousedown` on input, dispatch `mousedown` (with `bubbles: true`) on the MDFSelectBox container via JS `closest()`. React Select opens on `mousedown`, not `click`
- After opening: `page.keyboard.type()` to search, then click matching `MDFSelectBox__option`
- **Assign and Back buttons** (`#ENHAssignOBExp`, `#back-button-with-label`) are blocked by a background div intercepting pointer events — use `locator.evaluate("el => el.click()")` to bypass

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
- **Slider animation wait**: add `wait_for_timeout(3000)` after clicking `#openReportsToCustomSlider_Id` — on VPS, the search input (`#onReportsToSearch`) resolves as visible but times out because the slider is still animating/re-rendering

### Popup & Overlay Handling
- **"Remind me later"** popup may not appear every time — handled with try/except in `auth.py`
- **"Did you start this hire already?"** popup (`#showInProgressActiveEmpInfo_Id`) appears when ADP detects an in-progress hire — must be dismissed before filling form fields
- In-progress records from dry runs accumulate — delete them manually from ADP's In-Progress Hires list
- **Pendo product tour overlay** — `dismiss_pendo()` in `base_form.py` handles these; called after login and before Process button click. Tries `[id^='pendo-close']` then `button._pendo-close-guide`, falls back to JS `querySelectorAll('[id^="pendo-"]').forEach(el => el.remove())`
- **ADP loading spinner** — After Company Code selection, ADP shows a spinner while re-rendering dependent fields. Wait for spinner to disappear (`.sdf-spinner, .vdl-spinner, [class*='spinner'], [class*='loading']` → `state="hidden"`, 15s timeout) before clicking "Ask the New Hire"

### Dashboard URL Check Bug (CRITICAL — Fixed 2026-03-16)
- The login page URL contains `workforcenow.adp.com` in the `returnURL` query parameter: `https://online.adp.com/signin/v1/?...&returnURL=https://workforcenow.adp.com/&...`
- The old glob pattern `**/workforcenow.adp.com/**` matched this query parameter, causing `wait_for_url` to pass immediately even when the page was still on the login screen (login failed silently)
- **Fix**: use `https://workforcenow.adp.com/**` — matches only when the page is actually on the WFN domain
- This bug was masked before MFA handling was added because the page typically redirected before the URL check ran

### ADP Concurrent Session Issue
- ADP has a single active session policy — logging in from another location may invalidate the existing session
- If you log into ADP manually in a browser and close without logging out, the server-side session persists for 15–30 minutes
- The bot's login attempt during this window may fail silently (stays on login page)
- **Workaround**: log out of ADP before running the bot, or wait for the manual session to expire

### MFA Handling (Verified & Working 2026-03-22)
- **VPS always triggers MFA** — ADP sees unrecognized IP (DigitalOcean SFO3 datacenter) and requires identity verification on every login
- Detection: `h1:has-text('Verify Your Identity')` — must use `h1` specifically; `text=Verify Your Identity` matches 2 elements (h1 + span)
- SMS trigger: `page.locator("text=Send me a text message").click()`
- Code input: `page.get_by_label("Passcode")`
- Submit: progressive approach — `get_by_role("button", name="Submit")`, then `[type='submit']`, then `text=Submit`
- Full flow: `auth.py` detects MFA → triggers SMS → returns `mfa_required=True` → handler prompts user via Telegram → user replies with code → handler fills passcode + submits → continues to dashboard
- MFA auto-cancel timeout: 3 minutes; if user doesn't reply, browser is closed

### Headless Browser Detection (VPS / Production) — CRITICAL
- ADP detects headless Chromium and serves a different login page layout or blocks navigation entirely
- **`context.add_init_script(STEALTH_JS)`** is the correct approach — injects JavaScript BEFORE any page scripts on every navigation in the context. Do NOT use `page.evaluate()` which does not persist across navigations.
- The `STEALTH_JS` constant in `auth.py` covers 6 detection vectors:
  1. `navigator.webdriver` → `undefined` (primary detection vector)
  2. `navigator.plugins` → 3 fake Chrome plugins (headless has 0)
  3. `navigator.languages` → `['en-US', 'en']`
  4. `chrome.runtime` → exists (missing in headless)
  5. `permissions.query` → consistent notification permission state
  6. WebGL renderer → "Intel Iris OpenGL Engine" (headless shows "Google SwiftShader")
- Additional launch args: `--disable-blink-features=AutomationControlled`, `--disable-features=IsolateOrigins,site-per-process`
- Context options: realistic user agent (Chrome/131), viewport 1920x1080, locale `en-US`
- Playwright 1.40+ uses `--headless=new` mode by default — no explicit flag needed

### VPS Deployment (DigitalOcean — Working 2026-03-22)
- **Platform**: DigitalOcean droplet, Ubuntu 24.04, SFO3 region
- **User**: non-root user `big-al`, SSH key auth, UFW firewall enabled
- **SSH access**: `ssh hr-pilot` via `~/.ssh/config` alias on local machine
- **Service**: systemd unit `hr-pilot.service` — `sudo systemctl restart hr-pilot`, `journalctl -u hr-pilot -f`
- **Deploy routine**: `ssh hr-pilot` → `cd /home/big-al/hr-pilot && git pull && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; sudo systemctl restart hr-pilot`
- **__pycache__ clearing**: MUST clear after every `git pull` — stale `.pyc` files cause imports to use old code even after pulling new changes
- **All base_form.py utility defaults**: 20000ms — VPS is consistently slower than local dev
- **MFA from VPS**: ADP triggers MFA on every login from VPS due to unrecognized IP (SFO3 datacenter). Bot handles this automatically via Telegram relay
- **Pendo overlay dismissal**: `dismiss_pendo()` in `base_form.py` called after login and before Process button click; tries close buttons, falls back to JS removal
- **Validation popups**: "Go to Next Section" handled with combined `.or_()` locator (3 fallback selectors) + 20s timeout after Personal and Employment sections

### Security Management Portal (New Tab + Dojo Framework)
- Clicking "Security Management" link opens a **new browser tab** — must handle via `context.expect_page()` and switch to the new page
- The Security Management portal uses the **Dojo framework** (not SDF/React like the main WFN portal)
- Dojo element IDs are **dynamic** (e.g., `revit_form_Button_14` may change between sessions) — never rely on numeric IDs
- For Dojo buttons, use text-based selectors: `span[role="button"]:has(span.dijitButtonText:has-text("Yes"))`
- For Dojo dialogs, the popup container is `div.revitDialog3.dijitDialog`
- The PRC search form uses standard HTML inputs (`#empId`, `#formSaveButton`) — these are stable
- The employee checkbox uses a clickable image: `img[id*="tableGrid"][id*="cells[0]"]`
- The Issue PRC dropdown uses `#picEmailActions_arrow` — stable selector

### ADP Sticky Toolbar / Viewport Issues
- ADP has a sticky bottom toolbar that can overlay form elements
- `page.check()`, `page.click()`, and even `force=True` may fail when elements are behind this toolbar
- **Solution**: `page.locator(selector).evaluate("el => el.click()")`
- This fires a real DOM click event that React picks up, without needing viewport coordinates
- Use this pattern for any element that reports "outside of the viewport"
- Note: manually setting `.checked = true` + `dispatchEvent('change')` does NOT work — React ignores it. The native `.click()` fires a proper MouseEvent that React's synthetic event system intercepts.

### pydantic-settings `List[int]` Parsing Bug (CRITICAL)
- With `extra="allow"` in `model_config`, pydantic-settings v2.4+ tries to `json.loads()` ALL complex-typed fields (including `List[int]`) from env vars before validators run
- `json.loads("616520367,8620336711")` raises `SettingsError` — the `field_validator` never gets a chance to run
- **Fix**: declare `telegram_allowed_user_ids: str` (plain string, no JSON decoding), then expose the parsed list via a `@property`:
  ```python
  @property
  def allowed_user_ids(self) -> List[int]:
      return [int(uid.strip()) for uid in self.telegram_allowed_user_ids.split(",")]
  ```
- Use `settings.allowed_user_ids` everywhere (not `settings.telegram_allowed_user_ids`) for the integer list

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
| MFA prompt blocking login | Handled automatically — bot detects MFA, sends SMS, relays code prompt via Telegram |
| Login fails in headless mode on VPS | Stealth via `context.add_init_script(STEALTH_JS)` — covers webdriver, plugins, languages, chrome.runtime, permissions, WebGL |
| Navigation times out on VPS | Process button has retry with reload; all timeouts tuned for VPS latency |
| Pendo overlay blocks clicks | `dismiss_pendo()` called after login and before Process button click |
| Login "succeeds" but dashboard not loading | Check URL — old `**/workforcenow.adp.com/**` pattern matched login page `returnURL`; fixed to `https://workforcenow.adp.com/**` |
| Login fails after manual ADP session | ADP single-session policy — log out of ADP manually or wait 15–30 min for session expiry |
| Screenshot times out | `full_page=False` (viewport only) + 60s timeout; ADP full-page never stabilizes |
| Form field visible but times out | ADP re-renders DOM after dropdown selections; add settle waits + increase timeout |
| Reports To search input times out | Slider animation on VPS — add 3s wait after clicking Reports To button; element resolves visible but flickers during animation |
| Onboarding pencil icon click does nothing | Two DOM elements match — off-screen header button at y=-657 gets clicked instead. Pre-scroll modal into view, then use JS `isVisible()` filter (y >= -100) to skip off-screen elements |
| Onboarding dropdown not working | `#onboardingTemplateId` is a hidden MDFSelectBox input. `fill_mdf_dropdown()` can't click it. Use custom sequence: force-click input, dispatch focus + mousedown on input and container, then `keyboard.type()` to search |
| Onboarding Assign/Back button blocked | Background div intercepts pointer events on `#ENHAssignOBExp` and `#back-button-with-label`. Use `locator.evaluate("el => el.click()")` |
| Logs not appearing in journalctl | Module uses `logging.getLogger(__name__)` instead of `setup_logger(__name__)`. Fix: import and use `setup_logger` from `src/utils/logger` |
| Changes not taking effect after deploy | Stale `__pycache__` — clear with `find . -type d -name __pycache__ -exec rm -rf {} +` after `git pull` |

---

## Future Enhancements

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