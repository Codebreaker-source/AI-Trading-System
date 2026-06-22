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
