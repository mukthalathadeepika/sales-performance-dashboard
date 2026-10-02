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
    
    cards = page.locator('.kpi-card')
    print(f"Locator .kpi-card count: {cards.count()}")
    for i in range(cards.count()):
        print(f"Card {i} HTML:\n", cards.nth(i).evaluate("el => el.outerHTML"))
    
    kpi_grid = page.locator('.kpi-grid')
    print(f"Locator .kpi-grid count: {kpi_grid.count()}")
    if kpi_grid.count() > 0:
        print("kpi-grid HTML:\n", kpi_grid.first.evaluate("el => el.innerHTML"))
    else:
        print("No .kpi-grid found!")
        
    browser.close()
