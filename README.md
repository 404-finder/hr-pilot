# hr-pilot: Telegram-to-ADP HR Automation

Automated HR workflow system that processes new hires and terminations via Telegram bot with ADP Workforce Now integration.

## Features

- 🤖 Telegram bot interface for HR actions
- 🔐 Secure ADP login with MFA support
- 📝 Automated form filling for new hires and terminations
- ✅ Data validation using Pydantic models
- 📸 Debug screenshots on errors
- 🔒 User access control via whitelist

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

## Supported Commands

- `/newhire` - Add a new employee to ADP
- `/terminate` - Process an employee termination
- `/start` - Get started with the bot
- `/help` - Show help message
- `/cancel` - Cancel current operation

## Security

- Only whitelisted Telegram users can trigger automation
- Sensitive data (SSN, passwords) handled via SecretStr
- Headless browser operation in production
- Session cleanup after each run
- Audit logging for all actions

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete technical documentation.
