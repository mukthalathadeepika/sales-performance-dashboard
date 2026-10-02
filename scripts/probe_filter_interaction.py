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
    
    # Open filter expander
    expander = page.locator('details summary:has-text("Filter Controls")').first
    if expander.count() > 0:
        expander.click()
        page.wait_for_timeout(1000)
    
    reg_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Region"))')
    print("Region multiselect count:", reg_ms.count())
    
    # In Streamlit, typing into the multiselect input and pressing Enter selects the option!
    inp = reg_ms.locator('input')
    inp.click()
    page.wait_for_timeout(500)
    inp.type("West", delay=100)
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    
    # Check selected value tag
    tags = reg_ms.locator('[data-baseweb="tag"]').all_inner_texts()
    print("Selected tags in Region:", tags)
    
    # Click Apply Filters
    apply_btn = page.locator('[data-testid="stMain"] button:has-text("Apply Filters")').first
    print("Clicking Apply Filters...")
    apply_btn.click()
    page.wait_for_timeout(4000)
    
    banner = page.locator('.filter-status-banner').inner_text()
    print("Filter banner after Apply:\n", banner)
    
    kpis = page.locator('.kpi-card').all_inner_texts()
    print("KPI cards after Apply:")
    for c in kpis:
        lines = [l.strip() for l in c.split("\n") if l.strip()]
        print("  •", lines[0], "->", lines[1] if len(lines) > 1 else "")
        
    # Click Reset All Filters
    reset_btn = page.locator('[data-testid="stMain"] button:has-text("Reset All Filters")').first
    print("Clicking Reset All Filters...")
    reset_btn.click()
    page.wait_for_timeout(4000)
    
    restored_banner = page.locator('.filter-status-banner').inner_text()
    print("Filter banner after Reset:\n", restored_banner)
    
    restored_kpis = page.locator('.kpi-card').all_inner_texts()
    for c in restored_kpis:
        lines = [l.strip() for l in c.split("\n") if l.strip()]
        if "TOTAL SALES" in lines[0].upper():
            print("Restored Sales:", lines[1] if len(lines) > 1 else "")
            
    browser.close()
