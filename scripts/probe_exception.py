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
    
    caps = page.locator('[data-testid="stCaptionContainer"]').all_inner_texts()
    print("Captions:", caps)
    main_text = page.locator('[data-testid="stMain"]').inner_text()
    print("Main text snippet around error:")
    for line in main_text.split("\n"):
        if "Something went wrong" in line or "Traceback" in line or "Error" in line or "Exception" in line or "key" in line.lower():
            print("  >", line)
    
    browser.close()
