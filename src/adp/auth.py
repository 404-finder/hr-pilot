"""
ADP authentication module.

Handles login/logout and session management for ADP Workforce Now.
"""

import asyncio
from typing import Any, Tuple

from playwright.async_api import Browser, Page, async_playwright

from src.adp.base_form import dismiss_pendo
from src.adp.exceptions import LoginError
from src.adp.selectors.login import (
    NEXT_BUTTON,
    PASSWORD_INPUT,
    REMIND_ME_LATER_BUTTON,
    SIGN_IN_BUTTON,
    USERNAME_INPUT,
)
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Comprehensive stealth script injected BEFORE any page JS on every navigation.
# context.add_init_script() persists across navigations — unlike page.evaluate()
# which only runs on the current page context and is lost on goto().
STEALTH_JS = """
// 1. navigator.webdriver — primary headless detection vector
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. navigator.plugins — headless has 0 plugins, real Chrome has 3+
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer',
              description: 'Portable Document Format', length: 1 },
            { name: 'Chrome PDF Viewer',
              filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
              description: '', length: 1 },
            { name: 'Native Client', filename: 'internal-nacl-plugin',
              description: '', length: 1 },
        ];
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => arr.find(p => p.name === n);
        arr.refresh = () => {};
        return arr;
    }
});

// 3. navigator.languages — ensure consistent en-US
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// 4. chrome.runtime — missing in headless, present in real Chrome
if (!window.chrome) window.chrome = {};
if (!window.chrome.runtime) window.chrome.runtime = {};

// 5. permissions.query — headless returns different defaults for notifications
const originalQuery = window.navigator.permissions.query.bind(
    window.navigator.permissions
);
window.navigator.permissions.query = (params) => (
    params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(params)
);

// 6. WebGL renderer — headless shows "Google SwiftShader" which is a dead giveaway
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParam.call(this, param);
};
"""


async def _enter_password_and_sign_in(page: Page, password: str) -> None:
    """Fill password and click Sign In."""
    await page.fill(PASSWORD_INPUT, password)
    await page.click(SIGN_IN_BUTTON)


async def login_to_adp(username: str, password: str) -> Tuple[Any, Browser, Page, bool]:
    """Log into ADP WFN and return the Playwright instance, browser, page, and MFA flag.

    Implements retry logic with exponential backoff (3 attempts: 2s, 4s, 8s).
    Uses comprehensive browser stealth to avoid headless detection by ADP.

    If ADP presents a "Verify Your Identity" MFA page, triggers the SMS code
    send and returns with mfa_required=True. The page is left on the code entry
    screen; caller must collect the code from the user, fill it in, and submit.

    Args:
        username: ADP username.
        password: ADP password (plaintext).

    Returns:
        Tuple of (pw, Browser, Page, mfa_required):
            - pw: Playwright instance. Caller must call pw.stop() when done.
            - mfa_required=False: page is on the WFN dashboard, ready to navigate.
            - mfa_required=True: page is on the MFA code entry screen.

    Raises:
        LoginError: If login fails after max retries.
    """
    max_retries = 3
    backoff_delays = [2, 4, 8]  # seconds
    pw = None
    browser = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"ADP login attempt {attempt}/{max_retries}")

            # Launch browser with anti-detection args
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(
                headless=settings.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )

            # Inject stealth overrides BEFORE any page JS runs.
            # This persists across all navigations in this context — unlike
            # page.evaluate() which only affects the current page context.
            await context.add_init_script(STEALTH_JS)

            page = await context.new_page()

            # Navigate to login page
            logger.info("Navigating to ADP login URL")
            await page.goto(settings.adp_login_url, timeout=60000, wait_until="domcontentloaded")

            # Fill username and click next
            logger.info("Entering username")
            await page.wait_for_selector(USERNAME_INPUT, timeout=10000)
            await page.fill(USERNAME_INPUT, username)
            await page.click(NEXT_BUTTON)

            # Wait for password field to appear
            logger.info("Waiting for password field")
            await page.wait_for_selector(PASSWORD_INPUT, timeout=10000)

            await page.wait_for_timeout(3000)

            # Fill password and sign in (with timeout guard)
            logger.info("Entering password")
            try:
                await asyncio.wait_for(
                    _enter_password_and_sign_in(page, password),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error("Password entry/sign-in timed out after 30s")
                raise LoginError("Password entry timed out after 30s — ADP may be unresponsive")

            # Check for MFA before waiting for the dashboard
            await page.wait_for_timeout(5000)

            # Dismiss passkey/reminder popup if it appears (blocks dashboard redirect)
            try:
                remind_btn = page.locator(REMIND_ME_LATER_BUTTON)
                if await remind_btn.is_visible():
                    await remind_btn.click()
                    logger.info("Dismissed passkey/reminder popup")
                    await page.wait_for_timeout(2000)
            except Exception:
                pass

            mfa_detected = await page.locator("h1:has-text('Verify Your Identity')").is_visible()

            if mfa_detected:
                logger.info("MFA page detected — triggering SMS code")
                await page.locator("text=Send me a text message").click()
                await page.wait_for_timeout(2000)

                return pw, browser, page, True

            # Normal path — wait for dashboard URL
            logger.info("No MFA detected — waiting for dashboard redirect")
            await page.wait_for_url("https://workforcenow.adp.com/**", timeout=30000)

            # Wait for dashboard DOM to be ready before proceeding
            await page.wait_for_load_state("domcontentloaded")
            logger.info(f"Post-login URL: {page.url}")

            # Dismiss Pendo product tour overlay if present
            await dismiss_pendo(page)

            logger.info("Successfully logged into ADP")
            return pw, browser, page, False

        except Exception as e:
            logger.error(f"Login attempt {attempt} failed: {e}")

            # Close browser and stop Playwright to avoid leaking node processes
            try:
                await browser.close()
            except Exception:
                pass
            try:
                await pw.stop()
            except Exception:
                pass

            # If this was the last attempt, raise LoginError
            if attempt == max_retries:
                raise LoginError(f"Failed to login to ADP after {max_retries} attempts: {e}")

            # Otherwise, wait before retrying
            delay = backoff_delays[attempt - 1]
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)

    # This should never be reached due to the raise above, but for type safety
    raise LoginError(f"Failed to login to ADP after {max_retries} attempts")
