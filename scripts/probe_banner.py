import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1050})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3500)
    
    print("Banner count:", page.locator('.filter-status-banner').count())
    print("Pre blocks with banner:", page.locator('pre:has-text("filter-status-banner")').count())
    if page.locator('pre:has-text("filter-status-banner")').count() > 0:
        print("Found in pre block! Code block parsing occurred!")
        print(page.locator('pre:has-text("filter-status-banner")').first.inner_text()[:300])
    
    browser.close()
