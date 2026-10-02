import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1600, "height": 1000})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3000)
    print("H1:", page.locator("h1").all_inner_texts())
    print("ERRORS:", page.locator('[data-testid="stAlert"]').all_inner_texts())
    print("SWIPE COUNT:", page.locator(".swipe-card").count())
    print("MAIN TEXT SNIPPET:", page.locator('[data-testid="stMain"]').inner_text()[:600])
    page.screenshot(path="scripts/shots/test_load.png")
    b.close()
