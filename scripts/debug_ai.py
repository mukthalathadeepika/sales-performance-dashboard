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
    
    # Click AI Sales Assistant (index 3)
    page.locator('[data-testid="stRadio"] label').nth(3).click()
    page.wait_for_timeout(3000)
    print("AI ASSISTANT HEADER:", page.locator('h1').all_inner_texts())
    
    # Test typing in chat input
    chat_box = page.locator('[data-testid="stChatInput"] textarea')
    chat_box.fill("What is the total sales?")
    page.wait_for_timeout(500)
    
    # Click chat submit button
    submit_btn = page.locator('[data-testid="stChatInput"] button')
    if submit_btn.count() > 0:
        submit_btn.click()
    else:
        chat_box.press("Enter")
        
    page.wait_for_timeout(4000)
    page.screenshot(path=str(OUT / "e2e_03_ai_assistant_test.png"))
    
    main_text = page.locator('div.main, [data-testid="stMain"]').all_inner_texts()
    print("AI TEXT OUTPUT:\n", "\n".join(main_text[:2000]))
    
    b.close()
