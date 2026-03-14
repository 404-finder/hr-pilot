# hr-pilot: Telegram-to-ADP HR Automation

Automated HR workflow system that processes new hires via a Telegram bot with ADP Workforce Now browser automation.

## Features

- Telegram bot interface for HR actions
- Per-user ADP credentials mapped to Telegram user IDs
- Automated new hire form filling with dry-run preview before submission
- Personal Registration Code (PRC) delivery after hire submission
- Data validation using Pydantic models
- Debug screenshots at each form stage
- User access control via Telegram user ID whitelist

## Supported Stores

**Texas (ZKT - LC Texas LLC)**
| Store | Location |
|-------|----------|
| 39101 | Hewitt Drive |
| 39102 | Interstate 35 |
| 39103 | South Valley Mills |
| 39104 | North Valley Mills |

**Colorado (FND - LC CO LLC)**
| Store | Location |
|-------|----------|
| 33561 | Austin Bluffs Parkway |
| 33562 | Galley Road |
| 33563 | Constitution Avenue |
| 33564 | Cheyenne Meadows Road |
| 33565 | Mesa Ridge Parkway |
| 33566 | South Academy Boulevard |
| 33567 | Stetson Hills Boulevard |

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env with your credentials

# 5. Run the bot
python -m src.main
```

## Environment Variables

```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ALLOWED_USER_IDS=USER_ID_1,USER_ID_2

# One set per Telegram user — increment number for each user
ADP_USERNAME_1=username1
ADP_PASSWORD_1=password1
TELEGRAM_USER_ID_1=USER_ID_1

ADP_USERNAME_2=username2
ADP_PASSWORD_2=password2
TELEGRAM_USER_ID_2=USER_ID_2

HEADLESS=true
LOG_LEVEL=INFO
SCREENSHOT_DIR=screenshots
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/newhire` | Add a new employee to ADP |
| `/confirm` | Submit the pending new hire after dry-run review |
| `/cancel` | Cancel the current operation |
| `/start` | Welcome message |
| `/help` | Show usage instructions and field options |

## New Hire Message Format

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

**Field options:**
- **Store Number:** any store number listed above
- **Job Title:** `assist manager`, `co-manager`, `crew`, `dist manager`, `gen manager`, `manager`, `sal manager`
- **Work Schedule:** `full time`, `part time`
- **Pay Type:** `hourly`, `salary`
- **Reason:** `current`, `new hire` (defaults to `new hire`)

All field names and values are case-insensitive.

## New Hire Workflow

1. Send `/newhire` with employee details
2. Bot validates input and logs into ADP under your credentials
3. Form is filled in dry-run mode — a screenshot is sent for review
4. Reply `/confirm` to submit and send the Personal Registration Code (PRC)
5. Or `/cancel` to discard — auto-cancels after 5 minutes

## Running Tests

Always use the virtual environment Python:

```bash
.venv/Scripts/python.exe tests/test_login_nav.py
.venv/Scripts/python.exe tests/test_form_fill.py
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete technical documentation including ADP selector reference, known issues, and architecture notes.
