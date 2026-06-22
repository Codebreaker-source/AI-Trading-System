# Source Bundle: docs/full_source_bundles/12_colab_scripts.md


---

## `colab/keepalive.py`

```py
"""
Colab Keepalive Script
=======================
Uses Playwright to open Google Colab in Edge, check if the inference
notebook is still running, and restart it if disconnected.

Run via Windows Task Scheduler (FTMO_Colab_Keepalive, every 5 minutes):
  python C:\\...\\FTMO_System\\colab\\keepalive.py

Requires:
  pip install playwright

First run requires a one-time manual Google login in the dedicated
automation profile (see EDGE_USER_DATA below) — an Edge window will open,
log into the Google account that owns the Colab notebook, then close it.
"""

import os
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [KEEPALIVE] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "colab_keepalive.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── CONFIG ───────────────────────────────────────────────────────────────
# Paste your Colab notebook URL here after uploading to Google Drive.
# Format: https://colab.research.google.com/drive/YOUR_NOTEBOOK_ID
COLAB_NOTEBOOK_URL = os.environ.get(
    "COLAB_NOTEBOOK_URL",
    "https://colab.research.google.com/drive/1fmk1AQJAwyUmViu8M5-QiRVG5QxDdarG"
)

# Dedicated Edge profile for this automation (kept separate from your normal
# Edge profile so the scheduled task doesn't conflict with everyday browsing
# — Edge/Chromium locks a profile dir to one running instance at a time).
# First run requires a one-time manual Google login in this profile:
#   python colab/keepalive.py
# A new Edge window will open — log into the Google account that owns the
# Colab notebook, then close it. The session persists for future runs.
EDGE_USER_DATA = os.environ.get(
    "EDGE_USER_DATA",
    os.path.join(os.path.dirname(__file__), "edge_profile")
)

# How long to wait for Colab to connect before giving up (seconds)
CONNECT_TIMEOUT = 120

# ── MAIN ──────────────────────────────────────────────────────────────────

def is_colab_running(page) -> bool:
    """Return True if the Colab runtime is currently connected and running."""
    try:
        # Colab shows a green circle or 'Connected' text when runtime is active
        # Check for the connected RAM/disk indicator
        connected = page.locator('[data-testid="runtime-status-connected"]').count()
        if connected > 0:
            return True
        # Fallback: look for the green dot in the toolbar
        green = page.locator('.connected-icon').count()
        if green > 0:
            return True
        # Connected toolbar shows RAM/Disk usage instead of "Connect"
        ram = page.locator('text=/RAM/i').count()
        return ram > 0
    except Exception:
        return False


def click_run_all(page):
    """Trigger Runtime > Run all cells."""
    try:
        log.info("Clicking Runtime > Run all...")
        page.keyboard.press("Control+F9")   # Colab shortcut: Run all
        time.sleep(5)
        # Accept any 'Run anyway' dialog (e.g. 'This notebook is not authored by Google')
        run_anyway = page.locator('text="Run anyway"')
        if run_anyway.count() > 0:
            run_anyway.click()
            log.info("Accepted 'Run anyway' dialog")
        log.info("Run all triggered.")
    except Exception as e:
        log.error(f"click_run_all failed: {e}")


def connect_runtime(page):
    """Click the Connect button if runtime is disconnected."""
    try:
        connect_btn = page.locator('colab-connect-button, #connect, colab-toolbar-button#connect').first
        if connect_btn.count() == 0:
            connect_btn = page.locator('text="Connect"').first
        if connect_btn.count() > 0:
            connect_btn.click(force=True, timeout=10000)
            log.info("Clicked Connect button — waiting for runtime...")
            page.wait_for_selector('[data-testid="runtime-status-connected"], text=/RAM/i',
                                   timeout=CONNECT_TIMEOUT * 1000)
            log.info("Runtime connected.")
            return True
    except Exception as e:
        log.warning(f"connect_runtime: {e}")
    return False


def run_keepalive(login_mode: bool = False):
    if COLAB_NOTEBOOK_URL == "PASTE_YOUR_COLAB_URL_HERE":
        log.error("COLAB_NOTEBOOK_URL not set. Edit colab/keepalive.py and paste your notebook URL.")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    log.info(f"Starting keepalive check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Notebook URL: {COLAB_NOTEBOOK_URL}")

    with sync_playwright() as p:
        # Launch Edge using the existing user profile so Google login persists
        browser = p.chromium.launch_persistent_context(
            user_data_dir=EDGE_USER_DATA,
            headless=False,        # Must be visible to interact with Google auth
            channel="msedge",      # Use installed Edge, not bundled Chromium
            args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = browser.new_page()

        if login_mode:
            log.info("Login mode: opening Colab in Edge — log into Google in that window.")
            log.info("The browser will stay open for 3 minutes, then close automatically.")
            page.goto(COLAB_NOTEBOOK_URL, timeout=60000)
            time.sleep(180)
            browser.close()
            log.info("Login window closed. Session saved to the dedicated Edge profile.")
            return

        log.info("Navigating to Colab notebook...")
        page.goto(COLAB_NOTEBOOK_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(5)   # let Colab JS fully initialise

        if "--debug" in sys.argv:
            shot_path = os.path.join(os.path.dirname(__file__), "..", "logs", "colab_debug.png")
            page.screenshot(path=shot_path, full_page=True)
            log.info(f"[DEBUG] Screenshot saved to {shot_path}")
            log.info(f"[DEBUG] Page title: {page.title()}")
            log.info(f"[DEBUG] Page URL: {page.url}")

        if is_colab_running(page):
            log.info("[OK] Colab runtime is already running. Nothing to do.")
        else:
            log.info("[WARN] Colab runtime not running — attempting to reconnect and restart...")
            connected = connect_runtime(page)
            if connected:
                time.sleep(5)
                click_run_all(page)
                log.info("[OK] Notebook restarted successfully.")
            else:
                log.error("Could not connect runtime — manual intervention may be needed.")

        # Keep browser open briefly so we can confirm visually
        time.sleep(10)
        browser.close()

    log.info("Keepalive check complete.")


if __name__ == "__main__":
    run_keepalive(login_mode="--login" in sys.argv)

```

---

## `colab/find_notebook.py`

```py
import os
import time
from playwright.sync_api import sync_playwright

EDGE_USER_DATA = os.path.join(os.path.dirname(__file__), "edge_profile")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=EDGE_USER_DATA,
        headless=False,
        channel="msedge",
        args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )
    page = browser.new_page()

    # Try GitHub repo root
    page.goto("https://colab.research.google.com/", timeout=60000)
    time.sleep(6)
    print("URL after nav:", page.url)
    print("Title:", page.title())
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "logs", "colab_home.png"), full_page=True)

    # The "recent notebooks" picker may be a dialog
    text = page.locator("body").inner_text()
    with open(os.path.join(os.path.dirname(__file__), "..", "logs", "colab_home.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    time.sleep(15)
    browser.close()

```

---

## `colab/save_to_drive.py`

```py
"""
One-off helper: open the GitHub-hosted Colab notebook, dismiss the GitHub
auth dialog, and use File > Save a copy in Drive to create a Drive-hosted
copy that doesn't require GitHub auth on every load.
"""
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SAVE] %(message)s")
log = logging.getLogger(__name__)

EDGE_USER_DATA = os.path.join(os.path.dirname(__file__), "edge_profile")
COLAB_NOTEBOOK_URL = (
    "https://colab.research.google.com/github/Codebreaker-source/AI-Trading-System/"
    "blob/main/src/ftmo_system/colab/trading_inference.ipynb"
)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=EDGE_USER_DATA,
        headless=False,
        channel="msedge",
        args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )
    page = browser.new_page()
    log.info("Navigating to notebook...")
    page.goto(COLAB_NOTEBOOK_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    time.sleep(5)

    # Dismiss GitHub auth dialog if present
    cancel_btn = page.locator('text="Cancel"')
    if cancel_btn.count() > 0:
        log.info("Dismissing GitHub auth dialog...")
        cancel_btn.first.click()
        time.sleep(2)

    page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "logs", "save_step1.png"), full_page=True)

    # Open File menu
    log.info("Opening File menu...")
    file_menu = page.locator('text="File"').first
    file_menu.click()
    time.sleep(1)
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "logs", "save_step2.png"), full_page=True)

    # Click "Save a copy in Drive"
    save_item = page.locator('text="Save a copy in Drive"')
    if save_item.count() > 0:
        log.info("Clicking 'Save a copy in Drive'...")
        save_item.first.click()
        time.sleep(8)
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "logs", "save_step3.png"), full_page=True)

        # New tab may open with the Drive copy
        for pg in browser.pages:
            log.info(f"Open page URL: {pg.url}")
    else:
        log.error("Could not find 'Save a copy in Drive' menu item")

    time.sleep(15)
    browser.close()

```
