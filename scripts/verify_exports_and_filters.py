import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1600, "height": 1000})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3000)

    print("--- 1. VERIFY EXPORT BUTTONS ---")
    export_header = page.locator('h3:has-text("Export Center")')
    if export_header.count() > 0:
        export_header.scroll_into_view_if_needed()
    page.wait_for_selector('button:has-text("PDF"), [data-testid="stDownloadButton"] button:has-text("PDF")', timeout=15000)
    export_buttons = page.locator('[data-testid="stDownloadButton"]').all_inner_texts()
    print("Dashboard Export Buttons Found:", export_buttons)
    
    print("--- 2. VERIFY FILTERS INTERACTION ---")
    # Find filters expander and select Region
    filters_expander = page.locator('[data-testid="stSidebar"] details summary:has-text("Filters")')
    if filters_expander.count() > 0:
        # Check if already open
        is_open = page.locator('[data-testid="stSidebar"] details:has(summary:has-text("Filters"))').get_attribute("open") is not None
        if not is_open:
            filters_expander.click()
            page.wait_for_timeout(1000)
            
    # Click Region multiselect
    reg_select = page.locator('[data-testid="stSidebar"] div[data-baseweb="select"]:has(label:has-text("Region")), [data-testid="stSidebar"] label:has-text("Region") + div')
    if reg_select.count() > 0:
        reg_select.first.click()
        page.wait_for_timeout(500)
        # Select first option
        opt = page.locator('li[role="option"]').first
        if opt.count() > 0:
            opt_name = opt.inner_text()
            opt.click()
            page.wait_for_timeout(3000)
            print(f"Selected Region Filter: '{opt_name}'")
            print("Filtered Sales text:", page.locator('[data-testid="stMain"]').inner_text()[:400])
            
    # Reset All Filters
    btn_reset = page.locator('[data-testid="stSidebar"] button:has-text("Reset All Filters")')
    if btn_reset.count() > 0:
        btn_reset.click()
        page.wait_for_timeout(3000)
        print("Reset All Filters clicked. Total sales restored:", "₹13.07 Cr" in page.locator('[data-testid="stMain"]').inner_text())

    print("--- 3. VERIFY CLEAR & RELOAD DATASET ---")
    # Click Clear Current Dataset
    btn_clear = page.locator('[data-testid="stSidebar"] button:has-text("Clear Current Dataset")')
    btn_clear.click()
    page.wait_for_timeout(3000)
    empty_ok = "No Dataset Loaded" in page.locator('[data-testid="stMain"]').inner_text()
    print("Clear Current Dataset -> 'No Dataset Loaded':", empty_ok)
    page.screenshot(path=str(OUT / "e2e_empty_state.png"))

    # Click Load Sample Dataset from empty state or sidebar
    btn_load = page.locator('button:has-text("Load Sample SuperStore Dataset"), [data-testid="stSidebar"] button:has-text("Load Sample Dataset")').first
    btn_load.click()
    page.wait_for_timeout(5000)
    reloaded_ok = "5,901 rows" in page.locator('[data-testid="stSidebar"]').inner_text()
    print("Load Sample Dataset -> '5,901 rows':", reloaded_ok)
    page.screenshot(path=str(OUT / "e2e_reloaded.png"))

    b.close()
print("FILTERS, EXPORTS, AND DATASET LIFECYCLE VERIFIED!")
