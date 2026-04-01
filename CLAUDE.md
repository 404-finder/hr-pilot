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
| `/checkstatus` | Check Onboarding | Check new hire's onboarding task completion |

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
├── CLAUDE.md                      # This file (core project config)
├── CLAUDE_REFERENCE.md            # ADP quirks, bug fixes, troubleshooting
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
│   │   │   ├── common.py          # /start, /help, /cancel, /debug, error handler
│   │   │   ├── new_hire.py        # /newhire + /confirm + /cancel flow
│   │   │   ├── check_status.py    # /checkstatus handler
│   │   │   └── termination.py     # /terminate handler (not yet implemented)
│   │   └── parsers.py             # Parse telegram messages → dicts → models
│   ├── adp/
│   │   ├── __init__.py
│   │   ├── auth.py                # ADP login with retry logic
│   │   ├── base_form.py           # Shared form utilities (MDF dropdowns, etc.)
│   │   ├── navigation.py          # Navigate ADP menus and pages
│   │   ├── new_hire_form.py       # New hire form automation
│   │   ├── check_status.py        # Onboarding status check automation
│   │   ├── registration_code.py   # Send PRC via Security Management
│   │   ├── termination_form.py    # Termination form (TODO)
│   │   ├── exceptions.py          # Custom exception classes
│   │   └── selectors/
│   │       ├── __init__.py
│   │       ├── login.py           # Login page selectors (verified)
│   │       ├── new_hire.py        # New hire form selectors (verified)
│   │       ├── check_status.py    # Onboarding dashboard selectors
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

### `/checkstatus` Command

```
/checkstatus First Last mm/dd/yyyy
```

Example: `/checkstatus Carleton Haynes 03/01/2026`

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
    ssn: Optional[SecretStr] = None
    date_of_birth: Optional[date] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
```

- Manager auto-derived from `store_number` via `config_tables.LOCATION_MANAGERS`
- Home department auto-derived from `store_number` + `job_title` via `config_tables.get_home_department()`
- SSN, DOB, address delegated to the new hire via ADP onboarding flow

---

## Config Tables (`src/config_tables.py`)

| Table | Example Input → ADP Value |
|---|---|
| `REASON_FOR_HIRE` | "new hire" → "NEW - New Position" |
| `JOB_TITLES` | "crew" → "TEAMMEMB - TEAM MEMBER" |
| `WORK_SCHEDULE` | "part time" → "RPT - REGULAR PART TIME" |
| `STORE_LOCATIONS` | "39104" → "North Valley Mills" |
| `LOCATION_MANAGERS` | "39104" → `{"name": "Mary De Los Rios", "search": "De Los Rios"}` |
| `TAX_ID_TYPE` | "ssn" → "United States Social Security Number (SSN)" |

### Store Config (prefix-based)

Store number "39104" matches prefix "3910" → Texas config. Store number "33561" matches prefix "3356" → Colorado config. See `config_tables.py` for full `STORE_CONFIG` dict.

### Helper Functions

| Function | Purpose |
|---|---|
| `get_search_code(adp_value)` | Extract code before " - " for MDF dropdown search |
| `get_store_config(store_number)` | Look up STORE_CONFIG by prefix |
| `get_home_department(store_number, job_title_key)` | Build dept code: store + suffix |
| `get_everify_location(store_number)` | Look up store name from STORE_LOCATIONS |
| `get_manager(store_number)` | Returns `{"name": "Full Name", "search": "LastName"}` |

---

## ADP Automation Architecture

### Login (`src/adp/auth.py`)
- `login_to_adp(username, password)` → `(Browser, Page, bool)` — third value = `mfa_required`
- Credentials routed per Telegram user via `settings.get_adp_credentials(user_id)`
- Retry: 3 attempts, exponential backoff
- Stealth: `context.add_init_script(STEALTH_JS)` — 6 detection vectors
- MFA: detects `h1:has-text('Verify Your Identity')`, triggers SMS, returns `mfa_required=True`

### Navigation (`src/adp/navigation.py`)
- `navigate_to_new_hire(page)` — Process → Hire/Rehire → Go to Hire → HR PR New Hires
- `navigate_to_security_management(page)` — Setup → Security Management
- `navigate_to_registration_codes(page)` — People → Personal Registration Codes

### Base Form Utilities (`src/adp/base_form.py`)
- `fill_mdf_dropdown()` — ADP MDFSelectBox React Select pattern
- `click_visible_next_button()` — finds first visible Next button via JS
- `dismiss_pendo()` — removes Pendo product-tour overlays
- All default timeouts: 20s (tuned for VPS)

### New Hire Form (`src/adp/new_hire_form.py`)
- `fill_new_hire_form(page, hire, dry_run=True)` → `{"associate_id", "screenshot_path", "submitted", "warnings"}`
- Sections: Personal → Ask the New Hire modal → Employment → Payroll → Tax → DD (skip) → Emergency (skip) → Save & Exit

### Telegram Handler Flow
1. `/newhire` → parse → validate → login (+ MFA relay if needed) → navigate → fill (dry_run) → screenshot → `/confirm` → submit + PRC → done
2. Auto-cancel: 5min for form, 3min for MFA

---

## Critical Rules (Always Apply)

1. **Logging**: Use `from src.utils.logger import setup_logger` then `logger = setup_logger(__name__)`. NEVER use `logging.getLogger(__name__)`.
2. **VPS deploy**: After `git pull`, always `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null` then `sudo systemctl restart hr-pilot`.
3. **Timeouts**: All `wait_for_selector` = 20s minimum. Add `wait_for_timeout(3000)` after navigation clicks.
4. **Screenshots**: `full_page=False` (viewport only), 60s timeout.
5. **React inputs**: `page.click()` → `Ctrl+A` → `page.type()` → `Tab` (not `page.fill()`).
6. **MDFSelectBox**: Use `fill_mdf_dropdown()`, no trailing space in search_code.
7. **Stealth**: Must use `context.add_init_script(STEALTH_JS)`, not `page.evaluate()`.
8. **Blocked elements**: Use `locator.evaluate("el => el.click()")` for elements behind sticky toolbar or overlay divs.
9. **Playwright cleanup**: Every `browser.close()` must have a matching `await pw.stop()`. Every `context.user_data.pop("browser", None)` must have a matching `pop("pw", None)`. Leaked Playwright drivers consume ~54MB each and accumulate across runs.

> **For detailed ADP quirks, bug fixes, selector edge cases, and troubleshooting, see `CLAUDE_REFERENCE.md`.**

---

## Current Implementation Status (Last Updated: 2026-03-28)

### Completed Components

All `src/` modules working: config, config_tables, validators, models, auth, navigation, base_form, new_hire_form, registration_code, exceptions, selectors (login + new_hire), bot, parsers, handlers (common + new_hire), logger, screenshots. Tests passing.

### Completed Features
- Full new hire workflow (end-to-end, Texas + Colorado)
- MFA handling (auto-detect, SMS relay via Telegram)
- Multi-user ADP credentials
- VPS deployment with systemd
- Headless Chromium stealth (6 vectors)

### Known Bugs
1. **"Did you start this hire already?" popup** — needs auto-dismissal at start of `fill_new_hire_form()`

### Next Steps
1. `/checkstatus` command (onboarding task completion check)
2. Handle "Did you start this hire already?" popup
3. Implement termination workflow
4. Browser session persistence (skip MFA)

---

## Future Enhancements

- Dry run cleanup (cancel form to prevent in-progress accumulation)
- ConversationHandler for guided multi-step input
- CSV bulk upload via Telegram
- Pay changes / transfers workflows
- Scheduling for off-peak hours
- Audit trail logging
- ADP API integration (if access becomes available)
