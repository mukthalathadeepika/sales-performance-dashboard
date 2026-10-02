import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1050})
    page.goto("http://localhost:8502", timeout=30000)
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(2000)

    # Print all button texts
    buttons = page.locator("button").all_inner_texts()
    print("All buttons on 8502:", buttons)

    # Check for rerun / hamburger menu
    menu = page.locator('[data-testid="stMainMenu"], #MainMenu')
    print("MainMenu count:", menu.count())

    # Try keyboard shortcut 'r' to rerun
    page.keyboard.press("r")
    page.wait_for_timeout(3000)

    cards = page.locator(".kpi-card")
    print("Cards on 8502 after 'r':", cards.count())
    if cards.count() > 0:
        c0 = cards.first
        print("Card 0 text:", repr(c0.inner_text()))
        print("Card 0 html:", c0.evaluate("el => el.outerHTML"))

    browser.close()
