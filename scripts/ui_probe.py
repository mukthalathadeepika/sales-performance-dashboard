"""Live browser probe (dev tool). Usage: python scripts/ui_probe.py
Drives the running Streamlit app at http://localhost:8501 with Edge and saves screenshots to scripts/shots/."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://localhost:8501"
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)


def wait_ready(page, t=2500):
    page.wait_for_timeout(t)
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(800)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(URL)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=60000)
        wait_ready(page, 6000)
        page.screenshot(path=str(OUT / "01_dashboard.png"), full_page=True)
        print("TITLE", page.title())
        print("SIDEBAR_TEXT", page.inner_text('[data-testid="stSidebar"]')[:1500])
        print("DEPLOY", page.locator('[data-testid="stAppDeployButton"], .stDeployButton, [data-testid="stDeployButton"]').count())
        print("BODY_BG", page.evaluate("getComputedStyle(document.querySelector('[data-testid=stApp]')).backgroundColor"))
        print("MAIN_TEXT", page.inner_text('[data-testid="stMain"]')[:2500])
        print("EXCEPTIONS", page.locator('[data-testid="stException"]').count())
        b.close()


if __name__ == "__main__":
    main()
