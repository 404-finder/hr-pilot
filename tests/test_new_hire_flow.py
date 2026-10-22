"""
Mock-only tests for the /newhire flow in src/telegram_bot/handlers/new_hire.py.

No ADP or Telegram access: ADP calls, screenshot sends, and the watchdog are patched.
Verifies every exit path of _run_new_hire_flow cleans up and reports correctly.

Run: python -m pytest tests/test_new_hire_flow.py -v
"""

import asyncio
import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Settings are validated at import time — provide dummies if no .env is present
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_IDS", "1")
os.environ.setdefault("ADP_USERNAME_1", "dummy")
os.environ.setdefault("ADP_PASSWORD_1", "dummy")
os.environ.setdefault("TELEGRAM_USER_ID_1", "1")

import src.adp.new_hire_form as nhf  # noqa: E402
import src.telegram_bot.handlers.new_hire as nh  # noqa: E402
from src.adp.exceptions import FormSubmissionError  # noqa: E402
from src.adp.selectors.new_hire import NEXT_BUTTON_PRIMARY, SAVE_AND_EXIT_BUTTON  # noqa: E402

HIRE = SimpleNamespace(first_name="Jane", last_name="Doe", email="jane@example.com")
MANAGER_WARNING = "Manager search failed for 'X' — skipping manager assignment"
OK_RESULT = {
    "associate_id": "A1",
    "review_screenshot_path": "review.png",
    "screenshot_path": "saved.png",
    "warnings": [MANAGER_WARNING],
}


def _run_flow(fill, prc, send_fail=False, reply_fail=False):
    """Run _run_new_hire_flow with mocks and return what happened.

    Args:
        fill: Mock for fill_new_hire_form.
        prc: Mock for send_registration_code.
        send_fail: If True, every screenshot send raises.
        reply_fail: If True, every reply_text raises (after recording the text).

    Returns:
        SimpleNamespace with texts, photos, browser, pw, watchdog, user_data.
    """
    texts: list[str] = []
    photos: list[str] = []

    async def fake_reply(text):
        texts.append(text)
        if reply_fail:
            raise RuntimeError("telegram down")

    async def fake_send(message, path, caption):
        if send_fail:
            raise RuntimeError("telegram down")
        photos.append(caption)

    message = MagicMock()
    message.reply_text = AsyncMock(side_effect=fake_reply)
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={
        "browser": 1, "pw": 1, "page": 1, "hire": 1, "awaiting_mfa_code": True,
    })
    browser, pw = AsyncMock(), AsyncMock()

    with patch.object(nh, "navigate_to_new_hire", AsyncMock()), \
         patch.object(nh, "fill_new_hire_form", fill), \
         patch.object(nh, "send_registration_code", prc), \
         patch.object(nh, "send_and_delete_screenshot", fake_send), \
         patch.object(nh, "stop_watchdog", MagicMock()) as watchdog:
        asyncio.run(nh._run_new_hire_flow(update, context, pw, browser, "page", HIRE))

    return SimpleNamespace(
        texts=texts, photos=photos, browser=browser, pw=pw,
        watchdog=watchdog, user_data=context.user_data,
    )


def _assert_cleaned_up(r) -> None:
    """Assert browser closed, Playwright stopped, watchdog stopped, state cleared."""
    assert r.browser.close.await_count == 1
    assert r.pw.stop.await_count == 1
    assert r.watchdog.called
    assert r.user_data == {}


def test_success_sends_all_screenshots_and_warnings_first():
    r = _run_flow(AsyncMock(return_value=OK_RESULT), AsyncMock(return_value="prc.png"))
    _assert_cleaned_up(r)
    assert r.photos == [
        "Filled form (pre-save): Jane Doe",
        "[OK] Saved: Jane Doe (A1)",
        "[OK] Registration code sent to jane@example.com",
    ]
    assert len(r.texts) == 1
    summary = r.texts[0]
    assert summary.startswith("⚠️ CHECK DURING ADP REVIEW:")
    assert summary.index(MANAGER_WARNING) < summary.index("[OK] New hire saved")
    assert "Associate ID: A1" in summary


def test_fill_or_save_failure_reports_fail_with_screenshot():
    fill = AsyncMock(side_effect=FormSubmissionError("Save and Exit failed", "err.png"))
    prc = AsyncMock()
    r = _run_flow(fill, prc)
    _assert_cleaned_up(r)
    assert r.photos == ["Debug screenshot"]
    assert r.texts == ["[FAIL] Error processing new hire:\nSave and Exit failed"]
    prc.assert_not_awaited()


def test_prc_failure_reports_partial_with_associate_id():
    fill = AsyncMock(return_value={**OK_RESULT, "warnings": []})
    prc = AsyncMock(side_effect=FormSubmissionError("PRC boom", "prc_err.png"))
    r = _run_flow(fill, prc)
    _assert_cleaned_up(r)
    assert r.photos[-1] == "PRC error screenshot"
    assert len(r.texts) == 1
    assert r.texts[0].startswith("[PARTIAL] Form SAVED")
    assert "Associate ID: A1" in r.texts[0]


def test_post_save_screenshot_none_still_reports_success():
    fill = AsyncMock(return_value={
        **OK_RESULT,
        "screenshot_path": None,
        "warnings": ["Post-save screenshot failed — form WAS saved, verify in ADP"],
    })
    r = _run_flow(fill, AsyncMock(return_value="prc.png"))
    _assert_cleaned_up(r)
    assert "[OK] Saved: Jane Doe (A1)" not in r.photos
    assert "form WAS saved" in r.texts[0]
    assert "[OK] New hire saved" in r.texts[0]
    assert not any("[FAIL]" in t or "[PARTIAL]" in t for t in r.texts)


def test_screenshot_send_failure_still_sends_summary():
    r = _run_flow(
        AsyncMock(return_value=OK_RESULT), AsyncMock(return_value="prc.png"), send_fail=True
    )
    _assert_cleaned_up(r)
    assert r.photos == []
    assert len(r.texts) == 1
    assert "[OK] New hire saved" in r.texts[0]


def test_summary_reply_failure_after_prc_success_is_not_partial():
    r = _run_flow(
        AsyncMock(return_value=OK_RESULT), AsyncMock(return_value="prc.png"), reply_fail=True
    )
    _assert_cleaned_up(r)
    assert len(r.texts) == 1
    assert "[OK] New hire saved" in r.texts[0]
    assert not any("[PARTIAL]" in t for t in r.texts)


# ============================================================================
# Duplicate personal email (fe11842)
# ============================================================================

DUP_EMAIL_MSG = (
    "ADP rejected the email 'jane@example.com' — it already exists on another associate."
)


def _mock_form_page(selectors: list[str]) -> MagicMock:
    """Build a mock ADP page that walks fill_new_hire_form up to the modal save.

    Every selector passed to locator/click/wait_for_selector is recorded, and
    ADP shows the "unique email address" error after the modal save.

    Args:
        selectors: List that receives every selector the form touches.

    Returns:
        Mock Playwright page.
    """
    async def record(selector, *args, **kwargs):
        selectors.append(selector)

    async def evaluate(js, *args):
        if "createTreeWalker" in js:  # onboarding pencil-icon click
            return {"clicked": "pencil", "log": []}
        return False  # e.g. "There are no entries" manager check

    def locator(selector):
        selectors.append(selector)
        loc = MagicMock()
        loc.evaluate = AsyncMock()
        loc.count = AsyncMock(return_value=1)
        loc.all_inner_texts = AsyncMock(return_value=[])
        loc.first.wait_for = AsyncMock()
        loc.first.scroll_into_view_if_needed = AsyncMock()
        return loc

    dup_email = MagicMock()
    dup_email.count = AsyncMock(return_value=1)
    dup_email.first.is_visible = AsyncMock(return_value=True)

    page = MagicMock()
    page.wait_for_selector = AsyncMock(side_effect=record)
    page.click = AsyncMock(side_effect=record)
    page.fill = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.is_checked = AsyncMock(return_value=True)
    page.input_value = AsyncMock(return_value="A1")
    page.evaluate = AsyncMock(side_effect=evaluate)
    page.keyboard = MagicMock(press=AsyncMock(), type=AsyncMock())
    page.locator = MagicMock(side_effect=locator)
    page.get_by_text = MagicMock(return_value=dup_email)
    return page


def test_duplicate_email_raises_before_save_and_exit():
    selectors: list[str] = []
    page = _mock_form_page(selectors)
    hire = SimpleNamespace(
        first_name="Jane", last_name="Doe", email="jane@example.com", phone="555-123-4567",
        store_number="39104", job_title="crew", work_schedule="part time", pay_rate=15.5,
        start_date=date(2026, 11, 1), reason="new hire",
    )

    with patch.object(nhf, "fill_text_field", AsyncMock()), \
         patch.object(nhf, "fill_date_field", AsyncMock()), \
         patch.object(nhf, "fill_mdf_dropdown", AsyncMock()), \
         patch.object(nhf, "_select_onboarding_experience", AsyncMock()), \
         patch.object(nhf, "capture_screenshot", AsyncMock(return_value="err.png")):
        try:
            asyncio.run(nhf.fill_new_hire_form(page, hire, dry_run=False))
            raise AssertionError("fill_new_hire_form did not raise on duplicate email")
        except FormSubmissionError as e:
            error = e

    page.get_by_text.assert_called_with("unique email address")
    assert "already exists on another associate" in str(error)
    assert error.screenshot_path == "err.png"
    # Stopped at the modal save: never reached Employment, let alone Save & Exit
    assert NEXT_BUTTON_PRIMARY not in selectors
    assert SAVE_AND_EXIT_BUTTON not in selectors


def test_duplicate_email_failure_reports_fail_and_cleans_up():
    fill = AsyncMock(side_effect=FormSubmissionError(DUP_EMAIL_MSG, "err.png"))
    prc = AsyncMock()
    r = _run_flow(fill, prc)
    _assert_cleaned_up(r)
    assert r.photos == ["Debug screenshot"]
    assert r.texts == [f"[FAIL] Error processing new hire:\n{DUP_EMAIL_MSG}"]
    prc.assert_not_awaited()
