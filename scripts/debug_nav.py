import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1600, "height": 1000})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3000)
    
    # Click Sales Analysis (index 2)
    page.locator('[data-testid="stRadio"] label').nth(2).click()
    page.wait_for_timeout(3000)
    print("SALES ANALYSIS HEADER:", page.locator('h1').all_inner_texts())
    tabs = page.locator('[role="tab"], button[data-testid="stTab"], [data-baseweb="tab"]').all_inner_texts()
    print("TABS:", tabs)
    
    # Click 2nd tab (Date Comparison)
    page.locator('[role="tab"]').nth(1).click()
    page.wait_for_timeout(2000)
    print("AFTER CLICK TAB 2 (Date Comparison):")
    buttons = page.locator('[data-testid="stMain"] button').all_inner_texts()
    print("BUTTONS IN TAB 2:", [btn for btn in buttons if btn.strip()])
    
    # Click AI Sales Assistant (index 3)
    page.locator('[data-testid="stRadio"] label').nth(3).click()
    page.wait_for_timeout(3000)
    print("AI ASSISTANT HEADER:", page.locator('h1').all_inner_texts())
    chat_elements = page.locator('[data-testid="stChatInput"], [data-testid="stChatInputTextArea"], textarea').all_inner_texts()
    print("CHAT ELEMENTS COUNT:", page.locator('[data-testid="stChatInput"]').count())
    print("TEXTAREA COUNT:", page.locator('textarea').count())
    print("PLACEHOLDERS:", page.locator('textarea').evaluate_all("els => els.map(e => e.placeholder)"))

    b.close()
