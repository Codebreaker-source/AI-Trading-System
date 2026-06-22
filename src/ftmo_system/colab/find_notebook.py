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
