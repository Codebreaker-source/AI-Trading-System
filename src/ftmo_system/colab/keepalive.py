"""
Colab Keepalive Script
=======================
Uses Playwright to open Google Colab in Chrome, check if the inference
notebook is still running, and restart it if disconnected.

Run via Windows Task Scheduler:
  - Trigger: Daily at 07:45 UTC (before London open)
  - Action:  python C:\\...\\FTMO_System\\colab\\keepalive.py

Requires:
  pip install playwright
  playwright install chromium

IMPORTANT: Set COLAB_NOTEBOOK_URL below after uploading the notebook
to your Google Drive and copying its share URL.
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
            os.path.join(os.path.dirname(__file__), "..", "logs", "colab_keepalive.log")
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
    "PASTE_YOUR_COLAB_URL_HERE"
)

# Path to your Chrome user data directory (keeps Google login alive)
# Default Chrome profile path on Windows:
CHROME_USER_DATA = os.environ.get(
    "CHROME_USER_DATA",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
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
        return green > 0
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
        connect_btn = page.locator('text="Connect"').first
        if connect_btn.count() > 0:
            connect_btn.click()
            log.info("Clicked Connect button — waiting for runtime...")
            page.wait_for_selector('[data-testid="runtime-status-connected"]',
                                   timeout=CONNECT_TIMEOUT * 1000)
            log.info("Runtime connected.")
            return True
    except Exception as e:
        log.warning(f"connect_runtime: {e}")
    return False


def run_keepalive():
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
        # Launch Chrome using the existing user profile so Google login persists
        browser = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA,
            headless=False,        # Must be visible to interact with Google auth
            channel="chrome",      # Use installed Chrome, not bundled Chromium
            args=["--no-first-run", "--no-default-browser-check"],
        )

        page = browser.new_page()

        log.info("Navigating to Colab notebook...")
        page.goto(COLAB_NOTEBOOK_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(5)   # let Colab JS fully initialise

        if is_colab_running(page):
            log.info("✓ Colab runtime is already running. Nothing to do.")
        else:
            log.info("✗ Colab runtime not running — attempting to reconnect and restart...")
            connected = connect_runtime(page)
            if connected:
                time.sleep(5)
                click_run_all(page)
                log.info("✓ Notebook restarted successfully.")
            else:
                log.error("Could not connect runtime — manual intervention may be needed.")

        # Keep browser open briefly so we can confirm visually
        time.sleep(10)
        browser.close()

    log.info("Keepalive check complete.")


if __name__ == "__main__":
    run_keepalive()
