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
    
    # Check baseline KPI values
    vals = page.locator('.kpi-card .kpi-value').all_inner_texts()
    titles = page.locator('.kpi-card .kpi-title').all_inner_texts()
    print("Baseline KPIs:")
    for t, v in zip(titles, vals):
        print(f"  {t}: {v}")
    assert "₹13.07 Cr" in vals[0]
    
    # Filter by West
    expander = page.locator('details summary:has-text("Filter Controls")').first
    if expander.count() > 0:
        expander.click()
        page.wait_for_timeout(800)
    
    reg_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Region"))')
    inp = reg_ms.locator('input')
    inp.click()
    page.wait_for_timeout(400)
    inp.type("West", delay=100)
    page.wait_for_timeout(600)
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    
    # Apply
    page.locator('[data-testid="stMain"] button:has-text("Apply Filters")').first.click()
    page.wait_for_timeout(4000)
    
    filtered_vals = page.locator('.kpi-card .kpi-value').all_inner_texts()
    print("\nFiltered KPIs (Region = West):")
    for t, v in zip(titles, filtered_vals):
        print(f"  {t}: {v}")
    
    # Check that sales changed to West's sales
    print("Filtered Total Sales changed:", filtered_vals[0] != vals[0])
    assert filtered_vals[0] != vals[0], "Filtered sales should differ from baseline sales!"
    
    # Reset
    page.locator('[data-testid="stMain"] button:has-text("Reset All Filters")').first.click()
    page.wait_for_timeout(4000)
    
    restored_vals = page.locator('.kpi-card .kpi-value').all_inner_texts()
    print("\nRestored KPIs:")
    for t, v in zip(titles, restored_vals):
        print(f"  {t}: {v}")
    assert restored_vals[0] == vals[0], "Restored sales should match baseline sales ₹13.07 Cr!"
    
    print("\n✓ KPI filter application and reset cycle VERIFIED 100% PERFECT!")
    browser.close()
