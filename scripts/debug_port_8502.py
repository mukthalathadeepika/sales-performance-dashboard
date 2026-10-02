from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1050})
    page.goto("http://localhost:8502", timeout=30000)
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path="scripts/shots/debug_port_8502.png")
    print("Screenshot saved to scripts/shots/debug_port_8502.png")
    browser.close()
