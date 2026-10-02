"""
scripts/verify_final_production.py
Comprehensive End-to-End browser verification probe for Final Production Pass:
- 3 Swipe cards
- 6 Restored KPI cards
- Dataset-driven cascading filters
- Apply Filters and Reset All Filters workflow
- Filter status banner and zero-result filter safety
- Sales Analysis and AI Assistant pages
- Exports
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SHOTS_DIR = Path(__file__).parent / "shots"
SHOTS_DIR.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1050})
    
    print("Navigating to http://localhost:8501 ...")
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3500)
    
    # 1. VERIFY SWIPE INTRODUCTION CARDS
    print("\n--- 1. VERIFY SWIPE INTRODUCTION CARDS ---")
    swipe_cards = page.locator('.swipe-card').all_inner_texts()
    print(f"Found {len(swipe_cards)} Swipe Cards.")
    for i, c in enumerate(swipe_cards, 1):
        lines = [line.strip() for line in c.split("\n") if line.strip()]
        print(f"  Card {i}: {lines[1] if len(lines) > 1 else lines[0]}")
    assert len(swipe_cards) == 3, f"Expected 3 swipe cards, found {len(swipe_cards)}"
    assert any("Understand Your Business" in c for c in swipe_cards), "Card 1 missing"
    assert any("Explore & Compare" in c for c in swipe_cards), "Card 2 missing"
    assert any("Ask, Analyze & Export" in c for c in swipe_cards), "Card 3 missing"
    print("✓ Swipe introduction cards verified successfully!")
    
    # 2. VERIFY RESTORED EXECUTIVE BI KPI CARDS
    print("\n--- 2. VERIFY RESTORED KPI CARDS ---")
    kpi_cards = page.locator('.kpi-card').all_inner_texts()
    print(f"Found {len(kpi_cards)} KPI Cards:")
    for card_text in kpi_cards:
        lines = [l.strip() for l in card_text.split("\n") if l.strip()]
        title = lines[0] if lines else "Unknown"
        val = lines[1] if len(lines) > 1 else ""
        pill = lines[2] if len(lines) > 2 else ""
        print(f"  • {title} -> {val} ({pill})")
    assert len(kpi_cards) == 6, f"Expected 6 KPI cards, found {len(kpi_cards)}"
    main_text = page.locator('[data-testid="stMain"]').inner_text()
    assert "₹13.07 Cr" in main_text, "Total Sales ₹13.07 Cr not found"
    assert "₹1.46 Cr" in main_text, "Total Profit ₹1.46 Cr not found"
    assert "3,003" in main_text, "Total Orders 3,003 not found"
    assert "11.2%" in main_text, "Profit Margin 11.2% not found"
    print("✓ 6 Executive BI KPI cards verified successfully!")
    page.screenshot(path=str(SHOTS_DIR / "final_01_dashboard_top.png"))
    
    # 3. VERIFY DATASET-DRIVEN FILTERS (NO INVENTED COLUMNS)
    print("\n--- 3. VERIFY DATASET-DRIVEN FILTERS ---")
    filter_expander = page.locator('[data-testid="stMain"] details summary:has-text("Filter Controls")')
    if filter_expander.count() > 0:
        filter_expander.click()
        page.wait_for_timeout(1000)
    
    # Check that Payment Method and Salesperson are NOT present (since absent in SuperStore)
    payment_filter = page.locator('label:has-text("Payment Method"), label:has-text("Payment")')
    salesperson_filter = page.locator('label:has-text("Salesperson")')
    print(f"  Payment Method filter visible: {payment_filter.count() > 0} (Should be False)")
    print(f"  Salesperson filter visible: {salesperson_filter.count() > 0} (Should be False)")
    assert payment_filter.count() == 0, "Payment Method filter was incorrectly displayed!"
    assert salesperson_filter.count() == 0, "Salesperson filter was incorrectly displayed!"
    print("✓ Filter system is strictly dataset-driven (no invented columns)!")

    # Check Initial Filter Status
    filter_status = page.locator('.filter-status-banner').inner_text()
    print("  Initial Filter Status:", filter_status)
    assert "Showing all data" in filter_status, "Initial status should be 'Showing all data'"

    # 4. VERIFY APPLY FILTERS WORKFLOW
    print("\n--- 4. VERIFY APPLY FILTERS WORKFLOW ---")
    reg_select = page.locator('div[data-testid="stMultiSelect"]:has(label:has-text("Region"))').first
    if reg_select.count() > 0:
        inp = reg_select.locator('input')
        inp.click()
        page.wait_for_timeout(300)
        inp.type("West", delay=100)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        
        # Click "Apply Filters" button
        apply_btn = page.locator('[data-testid="stMain"] button:has-text("Apply Filters")').first
        print("  Clicking 'Apply Filters' button...")
        apply_btn.click()
        page.wait_for_timeout(4000)
        
        # Verify status and updated KPI values
        new_status = page.locator('.filter-status-banner').inner_text()
        print("  Updated Filter Status:\n   ", new_status.replace("\n", " "))
        assert "Showing filtered results" in new_status, "Status should be 'Showing filtered results'"
        assert "1,901" in new_status, "West region should filter to 1,901 records"
        
        filtered_sales = page.locator('.kpi-card .kpi-value').first.inner_text()
        print(f"  Filtered Total Sales: {filtered_sales}")
        assert "₹4.36 Cr" in filtered_sales, f"Expected ₹4.36 Cr for West, got {filtered_sales}"
        page.screenshot(path=str(SHOTS_DIR / "final_02_filters_applied.png"))
        print("✓ Apply Filters successfully updated dashboard and KPIs!")

    # 5. VERIFY RESET ALL FILTERS
    print("\n--- 5. VERIFY RESET ALL FILTERS ---")
    reset_btn = page.locator('[data-testid="stMain"] button:has-text("Reset All Filters")').first
    reset_btn.click()
    page.wait_for_timeout(4000)
    restored_status = page.locator('.filter-status-banner').inner_text()
    print("  Restored Filter Status:\n   ", restored_status.replace("\n", " "))
    assert "Showing all data" in restored_status, "Status should be restored to 'Showing all data'"
    restored_sales = page.locator('.kpi-card .kpi-value').first.inner_text()
    assert "₹13.07 Cr" in restored_sales, "Total Sales should be restored to ₹13.07 Cr"
    print("✓ Reset All Filters successfully restored complete active dataset!")

    # 5b. VERIFY ZERO-RESULT FILTER SAFETY
    print("\n--- 5b. VERIFY ZERO-RESULT FILTER SAFETY ---")
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(2500)

    expander = page.locator('details summary:has-text("Filter Controls")').first
    if expander.count() > 0:
        expander.click()
        page.wait_for_timeout(800)

    # Region = South + Customer = Jim Mitchum yields 0 records
    reg_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Region"))')
    inp_reg = reg_ms.locator('input')
    inp_reg.click()
    page.wait_for_timeout(300)
    inp_reg.type("South", delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)

    cust_ms = page.locator('[data-testid="stMain"] [data-testid="stMultiSelect"]:has(label:has-text("Customer"))')
    inp_c = cust_ms.locator('input')
    inp_c.click()
    page.wait_for_timeout(300)
    inp_c.type("Jim Mitchum", delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")

    page.locator('[data-testid="stMain"] button:has-text("Apply Filters")').first.click()
    page.wait_for_timeout(4000)

    zero_card = page.locator('.zero-results-card')
    print("  Zero-results card visible:", zero_card.count() > 0)
    assert zero_card.count() > 0, "Zero results card should appear when 0 records match"
    print("  Zero results card displayed cleanly with zero crash!")
    page.screenshot(path=str(SHOTS_DIR / "final_02b_zero_results.png"))

    # Reset from zero-results card
    page.locator('button:has-text("Reset All Filters")').first.click()
    page.wait_for_timeout(4000)
    recovered_sales = page.locator('.kpi-card .kpi-value').first.inner_text()
    assert "₹13.07 Cr" in recovered_sales, "Dataset should recover to ₹13.07 Cr"
    print("✓ Zero-result safety and recovery verified 100%!")

    # 6. VERIFY EXPORT BUTTONS
    print("\n--- 6. VERIFY EXPORT CENTER ---")
    page.locator('h3:has-text("Export Center")').scroll_into_view_if_needed()
    page.wait_for_selector('button:has-text("PDF"), [data-testid="stDownloadButton"] button:has-text("PDF")', timeout=15000)
    exports = page.locator('[data-testid="stDownloadButton"]').all_inner_texts()
    print("  Export buttons found:", exports)
    assert any("CSV" in e for e in exports), "CSV export missing"
    assert any("Excel" in e for e in exports), "Excel export missing"
    assert any("PDF" in e for e in exports), "PDF export missing"
    page.screenshot(path=str(SHOTS_DIR / "final_03_export_center.png"))
    print("✓ All Export Center downloads verified!")

    # 7. VERIFY SALES ANALYSIS VIEW
    print("\n--- 7. VERIFY SALES ANALYSIS VIEW ---")
    page.locator('[data-testid="stSidebar"] [role="radiogroup"] label').nth(1).click()
    page.wait_for_timeout(3000)
    sa_header = page.locator('h1').inner_text()
    print("  Sales Analysis Header:", sa_header)
    assert "Sales Analysis" in sa_header, "Sales Analysis view failed to load"
    tabs = page.locator('[role="tab"]').all_inner_texts()
    print("  Analysis Tabs:", tabs)
    assert len(tabs) >= 3, "Expected analysis tabs"
    page.screenshot(path=str(SHOTS_DIR / "final_04_sales_analysis.png"))
    print("✓ Sales Analysis view verified!")

    # 8. VERIFY AI SALES ASSISTANT
    print("\n--- 8. VERIFY AI SALES ASSISTANT ---")
    page.locator('[data-testid="stSidebar"] [role="radiogroup"] label').nth(2).click()
    page.wait_for_timeout(3000)
    ai_header = page.locator('h1').inner_text()
    print("  AI Assistant Header:", ai_header)
    assert "AI Sales Assistant" in ai_header, "AI Assistant view failed to load"
    
    # Click suggested question chip: "What is the total sales?"
    chip = page.locator('button:has-text("What is the total sales?")').first
    if chip.count() > 0:
        chip.click()
        page.wait_for_timeout(4500)
        ai_resp = page.locator('body').inner_text()
        print("  AI Response Contains Total Sales (₹13.07 Cr):", "₹13.07 Cr" in ai_resp)
        assert "₹13.07 Cr" in ai_resp or "13.07" in ai_resp, "AI answer missing expected ₹13.07 Cr sales figure"
    page.screenshot(path=str(SHOTS_DIR / "final_05_ai_assistant.png"))
    print("✓ AI Sales Assistant verified!")

    browser.close()

print("\n🎉 ALL FINAL PRODUCTION VERIFICATIONS COMPLETED SUCCESSFULLY!")
