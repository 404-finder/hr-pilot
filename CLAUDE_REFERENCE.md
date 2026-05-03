# CLAUDE_REFERENCE.md — Detailed Learnings, Bug Fixes & Troubleshooting

> **This file is supplementary.** Read it when working on ADP selectors, debugging VPS issues, or hitting edge cases. The core project config is in `CLAUDE.md`.

---

## ADP Navigation Timing

- Dashboard wait: `wait_for_load_state("domcontentloaded")` + 15s static buffer
- Process menu button: 60s timeout, automatic retry (screenshot + page reload + 15s + 60s retry) via `_wait_for_process_button()`
- All subsequent nav selectors: 20s timeout
- New tab detection: 10s; new tab load state: 60s
- Add `wait_for_timeout(3000)` after each section Next button click — ADP renders all sections simultaneously; next section is hidden until transition completes
- Form interactivity wait: 5s static before first field fill (VPS fields can be visible but not interactive)
- First field (`#Name\.first`) timeout: 30s (ADP may re-render form DOM after initial visibility)
- Company Code → Tax ID Type: 2s settle wait after company code, 20s timeout for Tax ID Type
- Spinner wait: up to 15s before "Ask the New Hire" modal
- Dashboard load time is inconsistent — navigation may intermittently fail; re-run

---

## Bug Fixes (Resolved)

### Reports To Slider Animation (Fixed 2026-03-16)
- Clicking `#openReportsToCustomSlider_Id` opens slider panel
- On VPS, slider animation takes several seconds — `#onReportsToSearch` resolves as visible but `wait_for_selector` times out (element flickers during animation)
- **Fix**: `wait_for_timeout(3000)` after clicking Reports To button, before waiting for search input

### Onboarding Experience Pencil Icon (Fixed 2026-03-22)
- Two "Assign onboarding experience" elements in DOM: one off-screen header (`#ENHAssignOnboarding` at y=-657), one in visible modal
- **Pre-scroll fix**: scroll `#ENHAskNewhire` / `[class*="askNewHire"]` / `[class*="prehire"]` into view, then scroll `text=Assign onboarding experience` into view, wait 1s
- **Fix**: JS `page.evaluate()` with `isVisible()` filter (`r.top >= -100 && r.top < window.innerHeight`) skips off-screen duplicate. Wrapped in `asyncio.wait_for(timeout=15)`

### Onboarding Experience Dropdown (Fixed 2026-03-22)
- `#onboardingTemplateId` is a hidden MDFSelectBox input — Playwright can't click directly, `fill_mdf_dropdown()` fails
- **Fix**: force-click hidden input, dispatch `focus` + `mousedown` on input, dispatch `mousedown` (bubbles: true) on MDFSelectBox container via JS `closest()`. React Select opens on `mousedown`, not `click`
- After opening: `page.keyboard.type()` to search, click matching `MDFSelectBox__option`
- **Assign/Back buttons** (`#ENHAssignOBExp`, `#back-button-with-label`) blocked by background div — use `locator.evaluate("el => el.click()")`

### Dashboard URL Check Bug (Fixed 2026-03-16)
- Login page URL contains `workforcenow.adp.com` in `returnURL` query parameter
- Old pattern `**/workforcenow.adp.com/**` matched query parameter — `wait_for_url` passed on login screen
- **Fix**: `https://workforcenow.adp.com/**` — matches only actual WFN domain
- Bug was masked before MFA handling was added

### Three Form-Fill Fixes (Fixed 2026-05-03)

These three issues blocked the new hire pipeline end-to-end. All three were diagnosed and fixed in the same session.

**Form I-9 selector (three layers of quirks).**
- The `wfn-radio-button` id `Form I-9 question – electronic` contains an en-dash (U+2013, written as `\u2013`), NOT a regular hyphen. Visually identical, semantically different. Use the `\u2013` escape in source for grep-safety.
- ADP renders the same id in two places: inside `#showPreHireModal_Id` (the modal — the target) and inside `#Employment` (a read-only mirror populated from the modal). Without modal scoping, Playwright strict mode raises "resolved to 2 elements".
- The `wfn-radio-button` wrapper is inert to programmatic clicks — both `page.click()` and `locator.evaluate("el => el.click()")` fire without error but the radio state never updates. Target the inner `sdf-radio-button[value="E"]` instead. SDF radios are clickable (same component family as manager picker and measurement-periods radios).
- **Final selector**: `#showPreHireModal_Id wfn-radio-button[id="Form I-9 question \u2013 electronic"] sdf-radio-button[value="E"]`
- I-9 must be selected AFTER SEI — ADP clears any default I-9 selection once SEI is filled, leaving the field blank. Legal compliance — hard-fail on click failure.

**Compensation Type regex anchor (single-word options).**
- `fill_mdf_dropdown()` builds an anchored regex `^\s*{search_code}\b` (case-insensitive) to disambiguate prefix matches.
- The `\b` word boundary fails when the search code is a prefix of a longer single word. `^\s*Hour\b` does NOT match `"Hourly"` because the character after `Hour` is `l` (a word character — no boundary).
- Compensation Type is the only dropdown in the form where option text is a single word. All other dropdowns follow the `CODE - Description` format where `\b` anchors against the trailing space/hyphen and works correctly.
- **Fix**: pass the full word `"Hourly"` as the search code, not `"Hour"`.

**Manager search disambiguation (Last, First format).**
- ADP's Reports To search returns ALL matches for the search term, not just direct reports. Searching by bare last name returns every person with that name in the system.
- When two managers share a last name (Gonzalez: Crystal and Josue), the search returns both and the form-fill code clicks the first radio non-deterministically. Wrong-manager assignment is silent.
- ADP accepts `"Last, First"` (comma + single space) format and narrows to one person. Verified manually for both Gonzalezes individually and for Wilder Chandler.
- **Fix**: store the search term in `LOCATION_MANAGERS` as `"Last, First"` per manager. The fallback to `manager["name"]` (full name) stays in place as a safety net.
- **Side discovery**: the previous `LOCATION_MANAGERS` had Wilder Chandler's first and last names backwards. He's Wilder (first) Chandler (last), not Chandler Wilder. The old `"search": "Wilder"` worked only because there's only one Wilder in the system.

---

## ADP Selector Patterns

### MDFSelectBox Dropdowns
- Most ADP dropdowns are MDFSelectBox React Select, NOT `<select>` elements
- Pattern: click → fill short code (no trailing space) → wait 1.5s → click option `[class*="MDFSelectBox__option"]:has-text("...")`
- `get_search_code(adp_value)` extracts code before " - "; returns first 3 chars if no " - "
- **Space-sensitive**: "BE " kills results, "BE" works
- `page.fill()` does NOT trigger React onChange

### React Input Fields (Pay Rate)
- `page.fill()` sets DOM value but React ignores it (no onChange)
- Fix: `page.click()` → `Control+A` → `page.type()` → `Tab`

### Ambiguous "Next" Buttons
- ADP keeps Next buttons for ALL sections in DOM simultaneously
- `button.vdl-button--primary:has-text("Next")` resolves to 5+ elements
- Use `click_visible_next_button(page)` — JS `offsetParent !== null` filter

### Manager Search (Reports To)
- Search does NOT work with full name as a single token (e.g., "Mary De Los Rios" returns no results)
- `LOCATION_MANAGERS` stores `{"name": "First Last", "search": "Last, First"}` — comma + single space disambiguates duplicate last names
- Form-fill code tries `manager["search"]` first, falls back to `manager["name"]` if "There are no entries"
- Check for "There are no entries" before radio button click
- Radio: `sdf-radio-button[role="radio"][aria-checked="false"]` → click first, verify `aria-checked="true"`
- On failure: `Escape` to dismiss slider, append to `warnings`, continue

### Selectors Strategy
- Text-based for stable elements: `button:has-text("Process")`
- ID selectors for form inputs: `#navigateToNewHireViewId`
- Attribute selectors for links: `a[href="#/Process/..."]`
- Shadow DOM for custom elements: `sdf-box:has-text("HR PR New Hires")`

---

## Popup & Overlay Handling

- **"Remind me later"** — may not appear; handled with try/except in `auth.py`
- **"Did you start this hire already?"** (`#showInProgressActiveEmpInfo_Id`) — must dismiss before form fill; in-progress records accumulate from dry runs
- **Pendo overlays** — `dismiss_pendo()` tries `[id^='pendo-close']`, then `button._pendo-close-guide`, falls back to JS `querySelectorAll('[id^="pendo-"]').forEach(el => el.remove())`
- **ADP spinner** — after Company Code, wait for `.sdf-spinner, .vdl-spinner, [class*='spinner'], [class*='loading']` → `state="hidden"`, 15s timeout

---

## ADP Sticky Toolbar / Viewport Issues

- Sticky bottom toolbar can overlay form elements
- `page.check()`, `page.click()`, even `force=True` may fail
- **Solution**: `page.locator(selector).evaluate("el => el.click()")`
- Manually setting `.checked = true` + `dispatchEvent('change')` does NOT work — React ignores it

---

## MFA Handling Details (Verified 2026-03-22)

- VPS always triggers MFA (unrecognized DigitalOcean IP)
- Detection: `h1:has-text('Verify Your Identity')` — must use `h1`; `text=Verify Your Identity` matches 2 elements
- SMS trigger: `page.locator("text=Send me a text message").click()`
- Code input: `page.get_by_label("Passcode")`
- Submit: progressive — `get_by_role("button", name="Submit")`, then `[type='submit']`, then `text=Submit`
- Auto-cancel: 3 minutes

---

## Headless Browser Stealth Details

- `context.add_init_script(STEALTH_JS)` — persists across navigations; `page.evaluate()` does NOT
- 6 vectors covered:
  1. `navigator.webdriver` → `undefined`
  2. `navigator.plugins` → 3 fake Chrome plugins
  3. `navigator.languages` → `['en-US', 'en']`
  4. `chrome.runtime` → exists
  5. `permissions.query` → consistent notification state
  6. WebGL renderer → "Intel Iris OpenGL Engine"
- Launch args: `--disable-blink-features=AutomationControlled`, `--disable-features=IsolateOrigins,site-per-process`
- Context: Chrome/131 user agent, 1920x1080 viewport, `en-US` locale

---

## VPS Deployment Details

- DigitalOcean droplet, Ubuntu 24.04, SFO3
- User: `big-al`, SSH key auth, UFW enabled
- SSH: `ssh hr-pilot` via `~/.ssh/config`
- Service: `hr-pilot.service` — `sudo systemctl restart hr-pilot`, `journalctl -u hr-pilot -f`
- Deploy: `ssh hr-pilot` → `cd /home/big-al/hr-pilot && git pull && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; sudo systemctl restart hr-pilot`

---

## Security Management Portal (Dojo Framework)

- "Security Management" opens a **new browser tab** — handle via `context.expect_page()`
- Uses **Dojo framework**, not SDF/React
- Dojo IDs are dynamic (e.g., `revit_form_Button_14` changes) — never rely on numeric IDs
- Buttons: `span[role="button"]:has(span.dijitButtonText:has-text("Yes"))`
- Dialogs: `div.revitDialog3.dijitDialog`
- PRC search: standard HTML (`#empId`, `#formSaveButton`) — stable
- Employee checkbox: `img[id*="tableGrid"][id*="cells[0]"]`
- Issue PRC dropdown: `#picEmailActions_arrow` — stable

---

## ADP Concurrent Session Issue

- ADP single active session policy — manual login invalidates bot session
- Manual session persists 15–30 min after closing browser
- **Workaround**: log out of ADP manually or wait for expiry

---

## Playwright Resource Cleanup

- Every call to `async_playwright().start()` spawns a Node.js driver process (~54MB)
- `browser.close()` only kills Chromium — the Playwright driver (`pw`) survives
- Must call `await pw.stop()` at every cleanup point or processes accumulate
- On a 2GB VPS, 28 leaked processes consumed 1.5GB over 3 days (March 2026 incident)
- Symptoms: intermittent login timeouts, wrong screenshots from stale sessions, "Did you start this hire already?" popups
- `login_to_adp()` returns `(pw, browser, page, mfa_required)` — callers must store `pw` in `context.user_data` and stop it on every exit path
- Rule: every `browser.close()` must have a matching `pw.stop()`, every `pop("browser")` must have a matching `pop("pw")`
- Diagnostic: `ps aux | grep -i playwright | grep -v grep` should show zero processes after a completed run

---

## pydantic-settings `List[int]` Bug

- With `extra="allow"`, pydantic-settings tries `json.loads()` on complex-typed fields before validators
- **Fix**: declare `telegram_allowed_user_ids: str`, expose via `@property`:
  ```python
  @property
  def allowed_user_ids(self) -> List[int]:
      return [int(uid.strip()) for uid in self.telegram_allowed_user_ids.split(",")]
  ```

---

## Testing Notes

- Always use venv: `.venv/Scripts/python.exe tests/test_form_fill.py`
- Install browsers: `python -m playwright install chromium`
- Windows encoding: use `[OK]`/`[FAIL]` instead of emoji

---

## Common Issues & Troubleshooting

| Issue | Solution |
|---|---|
| ADP selectors broken | Inspect with DevTools, update `selectors/` |
| Playwright times out | Increase timeout, check network |
| Dropdown not selecting | `fill_mdf_dropdown()`, no trailing space |
| Pay rate not filling | `click()` + `Ctrl+A` + `type()` + `Tab` |
| "Next" button does nothing | `click_visible_next_button()` |
| Manager search no results | `manager["search"]` is `"Last, First"`; falls back to `manager["name"]` if no entries |
| Reports To slider timeout | 3s wait after clicking button |
| Onboarding pencil icon wrong | JS `isVisible()` filter for y-position |
| Onboarding dropdown fails | Custom mousedown sequence, not `fill_mdf_dropdown()` |
| Assign/Back button blocked | `locator.evaluate("el => el.click()")` |
| Logs missing in journalctl | Use `setup_logger()` not `logging.getLogger()` |
| Changes not taking effect | Clear `__pycache__` after `git pull` |
| Login succeeds but no dashboard | URL pattern bug — use `https://workforcenow.adp.com/**` |
| Login fails after manual session | ADP single-session — wait 15-30 min |
| Screenshot times out | `full_page=False` + 60s timeout |
| Pendo blocks clicks | `dismiss_pendo()` after login and before Process button |
| Navigation intermittent | Dashboard load variable; re-run |
| I-9 click silently fails, modal save rejects | Target inner `sdf-radio-button[value="E"]` scoped to `#showPreHireModal_Id`, not the `wfn-radio-button` wrapper |
| Single-word dropdown option times out (e.g., "Hourly") | Pass full word as search code; `\b` anchor fails mid-word |
| Manager search returns wrong person when last names collide | Store search as `"Last, First"` in `LOCATION_MANAGERS` |
| Code change deployed but not picked up by running bot | `git pull` does not restart the service. Run `sudo systemctl restart hr-pilot`. Verify with `systemctl status hr-pilot \| head -3` (Active: since timestamp must be after the deploy) |

---

## Swap Setup (2GB Safety Net)

- 2GB VPS with no swap caused intermittent Chromium launch failures when memory was tight
- Added 2GB swap file as overflow safety net (March 2026)
- Commands used:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
- Persists across reboots via /etc/fstab entry
- Verify with `free -h` — Swap row should show 2.0Gi
- No additional DigitalOcean cost — uses existing disk space

---

## SSH Quick Connect Setup

- SSH config file location (Windows): `~/.ssh/config`
- Config:
```
Host hr-pilot
    HostName 143.198.50.169
    User big-al
    IdentityFile ~/.ssh/vps-do-key
```
- Connect with: `ssh hr-pilot` (no need to type user, IP, or key path)
- SSH key (`vps-do-key`) stored in `~/.ssh/` — private key stays local, public key is on the VPS in `/home/big-al/.ssh/authorized_keys`
- DigitalOcean credentials and VPS access info stored in Bitwarden (Infrastructure or DevOps folder)
