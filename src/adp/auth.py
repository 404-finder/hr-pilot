"""
ADP login/logout and session management.

Handles authentication to ADP Workforce Now including MFA (TOTP).
"""

# TODO: Implement login_to_adp() -> Page
#       - Launch Playwright browser
#       - Navigate to ADP login URL
#       - Fill username and password
#       - Handle MFA with pyotp if configured
#       - Wait for successful redirect to dashboard
#       - Return authenticated page
# TODO: Implement logout_from_adp(page: Page)
# TODO: Implement retry logic with exponential backoff
# TODO: Raise LoginError on failure
