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
    
    # Inspect first column
    cols = page.locator('[data-testid="stColumn"]')
    print(f"Total stColumn count: {cols.count()}")
    for i in range(min(6, cols.count())):
        col = cols.nth(i)
        print(f"\n--- Column {i} ---")
        print("Text:", repr(col.inner_text()))
        card = col.locator('.kpi-card')
        print("kpi-card count in col:", card.count())
        if card.count() > 0:
            bg = card.evaluate("el => window.getComputedStyle(el).backgroundColor")
            border = card.evaluate("el => window.getComputedStyle(el).border")
            padding = card.evaluate("el => window.getComputedStyle(el).padding")
            display = card.evaluate("el => window.getComputedStyle(el).display")
            print(f"kpi-card computed style: bg={bg}, border={border}, padding={padding}, display={display}")
            print("OuterHTML:\n", card.evaluate("el => el.outerHTML"))
            
    browser.close()
