# CLAUDE.md — hr-pilot: Telegram-to-ADP HR Automation

## User Interaction
- Be concise and professional
- Present code first then explain
- Ask clarifying questions when unsure
- Favor readability over fancy solutions
- Print statements in code are short yet informative

## Project Overview

Python automation: Telegram Bot → parse message → Playwright logs into
ADP Workforce Now → fills HR forms → reports status back to Telegram.

Commands: `/newhire`, `/terminate` (TODO), `/checkstatus`

## Tech Stack

| Component | Library |
|---|---|
| Telegram Bot | `python-telegram-bot` (v20+, with `[job-queue]` extra) |
| Browser Automation | `playwright` (async API) |
| Config Management | `python-dotenv` |
| Data Validation | `pydantic` (v2+) |
| Settings | `pydantic-settings` |

## Coding Standards

- PEP 8, type hints on all signatures, `async`/`await` throughout.
- Never log sensitive fields. Use `pydantic.SecretStr` for passwords/SSNs.
- Google-style docstrings on all public functions and classes.
- Keep functions small and single-purpose.
- Use `logging` module — never `print()` (except test scripts).
- `UPPER_SNAKE_CASE` constants, `PascalCase` classes, `snake_case` functions/variables.
- All packages installed in `.venv`.

## Critical Rules (Always Apply)

1. **Logging**: `from src.utils.logger import setup_logger` then `logger = setup_logger(__name__)`. NEVER `logging.getLogger(__name__)`.
2. **VPS deploy**: After `git pull`, always `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null` then `sudo systemctl restart hr-pilot`.
3. **Timeouts**: All `wait_for_selector` = 20s minimum. Add `wait_for_timeout(3000)` after navigation clicks.
4. **Screenshots**: `full_page=False` (viewport only), 60s timeout.
5. **React inputs**: `page.click()` → `Ctrl+A` → `page.type()` → `Tab` (not `page.fill()`).
6. **MDFSelectBox**: Use `fill_mdf_dropdown()`, no trailing space in search_code.
7. **Stealth**: Must use `context.add_init_script(STEALTH_JS)`, not `page.evaluate()`.
8. **Blocked elements**: Use `locator.evaluate("el => el.click()")` for elements behind overlay divs.
9. **Playwright cleanup**: Every `browser.close()` must have `await pw.stop()`. Every `pop("browser")` must have `pop("pw")`. Leaked drivers consume ~54MB each.
10. **Watchdog**: All long-running handlers must call `start_watchdog()` before ADP login and `stop_watchdog()` in every exit path. See `src/telegram_bot/watchdog.py`.

## Handler Flow

1. `/newhire` → parse → validate → watchdog start → login (+ MFA relay) → navigate → fill (dry_run) → screenshot → `/confirm` → submit + PRC → watchdog stop → done
2. Auto-cancel: 5min for form confirmation, 3min for MFA code, 4min for watchdog first alert

## Key Reference Files

- `CLAUDE_REFERENCE.md` — ADP quirks, resolved bugs, selector edge cases, troubleshooting
- `ADP_SELECTORS_REFERENCE.md` — Complete ADP selector documentation
- `src/config_tables.py` — ADP dropdown mappings, store configs, helper functions
- `src/adp/selectors/` — All CSS selectors organized by page

## Current Status (2026-04-02)

### Working
- Full new hire workflow (Texas + Colorado, end-to-end)
- MFA handling (auto-detect, SMS relay via Telegram)
- Passkey popup dismissal (post-login)
- Onboarding dropdown retry (3 attempts)
- Watchdog timer for long-running operations
- Multi-user ADP credentials
- VPS deployment with systemd

### Known Bugs
1. **"Did you start this hire already?" popup** — needs auto-dismissal at start of `fill_new_hire_form()`

### Next Steps
1. Handle "Did you start this hire already?" popup
2. Implement termination workflow
3. Browser session persistence (skip MFA)