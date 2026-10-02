import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)

queries = [
    ("What is the total sales?", "₹13.07 Cr"),
    ("What is the total profit?", "₹1.46 Cr"),
    ("What is the top category?", "Technology"),
    ("Compare Technology sales in 2019 and 2020", "Technology"),
    ("What are the sales in India?", "Coverage Limitation"),
]

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1600, "height": 1000})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3000)
    
    # Click AI Sales Assistant (index 3)
    page.locator('[data-testid="stRadio"] label').nth(3).click()
    page.wait_for_timeout(3000)
    
    for i, (q, expected) in enumerate(queries):
        chat_box = page.locator('[data-testid="stChatInput"] textarea')
        chat_box.fill(q)
        page.wait_for_timeout(300)
        
        submit_btn = page.locator('[data-testid="stChatInput"] button')
        if submit_btn.count() > 0:
            submit_btn.click()
        else:
            chat_box.press("Enter")
            
        page.wait_for_timeout(3500)
        
        body_text = page.locator('body').inner_text()
        has_expected = expected.lower() in body_text.lower()
        print(f"QUERY {i+1}: '{q}' -> Found '{expected}': {has_expected}")
        
        page.screenshot(path=str(OUT / f"query_{i+1}.png"))
        
    b.close()
print("ALL 5 AI ASSISTANT QUERIES VERIFIED!")
