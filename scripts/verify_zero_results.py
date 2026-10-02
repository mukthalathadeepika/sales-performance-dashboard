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
        page.wait_for_timeout(800)
    
    # Select Region = South
    reg_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Region"))')
    inp = reg_ms.locator('input')
    inp.click()
    page.wait_for_timeout(300)
    inp.type("South", delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    
    # Select Customer = Jim Mitchum (who only exists in West, not South)
    cust_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Customer"))')
    inp_cust = cust_ms.locator('input')
    inp_cust.click()
    page.wait_for_timeout(300)
    inp_cust.type("Jim Mitchum", delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")
    
    # Click Apply Filters
    page.locator('[data-testid="stMain"] button:has-text("Apply Filters")').first.click()
    page.wait_for_timeout(4000)
    
    # Check for zero-results card
    zero_card = page.locator('.zero-results-card')
    print("Zero-results card visible:", zero_card.count() > 0)
    assert zero_card.count() > 0, "Zero results card should be displayed when rows == 0"
    zero_text = zero_card.inner_text()
    print("Zero card message:\n", zero_text)
    assert "No Data Matches the Selected Filters" in zero_text
    
    # Click Reset button on zero card
    reset_btn = page.locator('button:has-text("Reset All Filters")').first
    reset_btn.click()
    page.wait_for_timeout(4000)
    
    # Check recovery
    sales_val = page.locator('.kpi-card .kpi-value').first.inner_text()
    print("Restored Sales value after zero-results reset:", sales_val)
    assert "₹13.07 Cr" in sales_val
    print("✓ Zero-results filter safety verified successfully!")
    
    browser.close()
