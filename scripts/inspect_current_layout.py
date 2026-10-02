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
    
    page.screenshot(path="scripts/shots/current_dashboard_view.png")
    
    # Check computed style of .kpi-grid and .kpi-card
    grid = page.locator('.kpi-grid').first
    if grid.count() > 0:
        display = grid.evaluate("el => window.getComputedStyle(el).display")
        cols = grid.evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
        print(f"kpi-grid display: {display}, gridTemplateColumns: {cols}")
    
    cards = page.locator('.kpi-card')
    print(f"Cards count: {cards.count()}")
    for i in range(cards.count()):
        bbox = cards.nth(i).bounding_box()
        print(f"Card {i} bbox: {bbox}")
        
    browser.close()
