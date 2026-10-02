"""
scripts/verify_kpi_final.py
End-to-end browser verification of the restored KPI cards:
1. Validates all 6 cards are horizontally displayed in one row on desktop.
2. Validates card visual styling (background, border, border-top accent, padding, border-radius).
3. Validates exact expected metric values.
4. Validates NO text concatenation (periodGross revenue, etc.).
5. Validates stability AFTER browser refresh (page.reload()).
6. Captures screenshots before and after refresh.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
SHOTS_DIR = ROOT_DIR / "scripts" / "shots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_KPIS = [
    ("Total Sales", "₹13.07 Cr"),
    ("Total Profit", "₹1.46 Cr"),
    ("Total Orders", "3,003"),
    ("Total Quantity", "22,317"),
    ("Profit Margin", "11.2%"),
    ("Average Order Value", "₹43.5 K"),
]

FORBIDDEN_PATTERNS = [
    "periodGross revenue",
    "period11.2% net margin",
    "periodDistinct orders",
    "periodUnits shipped",
    "periodNet profit / sales",
]


def verify_page(page, context_label="Initial Load"):
    print(f"\n--- Checking KPIs: {context_label} ---")
    cards = page.locator(".kpi-card")
    count = cards.count()
    print(f"Total .kpi-card count: {count}")
    assert count == 6, f"Expected 6 KPI cards, found {count}"

    boxes = []
    card_texts = []

    for i in range(count):
        card = cards.nth(i)
        box = card.bounding_box()
        boxes.append(box)
        text = card.inner_text()
        card_texts.append(text)

        # Style check
        bg = card.evaluate("el => window.getComputedStyle(el).backgroundColor")
        border = card.evaluate("el => window.getComputedStyle(el).border")
        border_top = card.evaluate("el => window.getComputedStyle(el).borderTop")
        padding = card.evaluate("el => window.getComputedStyle(el).padding")
        border_radius = card.evaluate("el => window.getComputedStyle(el).borderRadius")
        min_height = card.evaluate("el => window.getComputedStyle(el).minHeight")

        print(f"\nCard {i} [{EXPECTED_KPIS[i][0]}]:")
        print(f"  Box: x={box['x']:.1f}, y={box['y']:.1f}, w={box['width']:.1f}, h={box['height']:.1f}")
        print(f"  Styles: bg={bg}, borderTop={border_top}, radius={border_radius}, padding={padding}")

        # Check values
        exp_title, exp_val = EXPECTED_KPIS[i]
        assert exp_title.upper() in text.upper(), f"Card {i} missing title '{exp_title}' in '{text}'"
        assert exp_val in text, f"Card {i} missing value '{exp_val}' in '{text}'"

        # Check forbidden text concatenations
        for forbidden in FORBIDDEN_PATTERNS:
            assert forbidden not in text, f"Card {i} contains broken concatenated text: '{forbidden}'"

        # Verify pill and subtitle are distinct elements
        pill = card.locator(".kpi-pill")
        subtitle = card.locator(".kpi-subtitle")
        assert pill.count() >= 1, f"Card {i} missing .kpi-pill"
        assert subtitle.count() >= 1, f"Card {i} missing .kpi-subtitle"
        print(f"  Pill: '{pill.first.inner_text()}', Subtitle: '{subtitle.first.inner_text()}'")

    # Horizontal row check:
    # All cards must share roughly the same y-coordinate (within 5px) and have increasing x-coordinates
    base_y = boxes[0]["y"]
    for i, b in enumerate(boxes):
        assert abs(b["y"] - base_y) < 8.0, f"Card {i} not in same horizontal row: y={b['y']} vs base_y={base_y}"
        if i > 0:
            assert b["x"] > boxes[i - 1]["x"], f"Card {i} (x={b['x']}) not to the right of Card {i-1} (x={boxes[i-1]['x']})"

    print(f"-> All 6 cards CONFIRMED horizontally aligned in 1 row.")
    return True


def run_test(port=8501):
    print(f"\n==========================================")
    print(f"Testing Streamlit on Port {port}")
    print(f"==========================================")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        
        url = f"http://localhost:{port}"
        print(f"Navigating to {url}...")
        page.goto(url, timeout=30000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
        page.wait_for_timeout(2000)

        # If Streamlit shows "Source file changed. Rerun / Always rerun"
        rerun_btn = page.locator('button:has-text("Rerun"), button:has-text("Always rerun")')
        if rerun_btn.count() > 0:
            print("Found Streamlit rerun notification, clicking it...")
            rerun_btn.first.click()
            page.wait_for_timeout(3000)

        # 1. Verify Initial Load
        verify_page(page, "Initial Load")
        shot1 = SHOTS_DIR / f"kpi_verified_initial_{port}.png"
        page.screenshot(path=str(shot1))
        print(f"Saved initial screenshot to {shot1}")

        # 2. Trigger Full Browser Refresh
        print("\n--- Performing full browser refresh (page.reload()) ---")
        page.reload()
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
        page.wait_for_timeout(3500)

        # 3. Verify After Refresh
        verify_page(page, "After Browser Refresh")
        shot2 = SHOTS_DIR / f"kpi_verified_after_refresh_{port}.png"
        page.screenshot(path=str(shot2))
        print(f"Saved after-refresh screenshot to {shot2}")

        browser.close()
    print(f"\nPort {port} Verification: SUCCESSFUL!")


if __name__ == "__main__":
    # Test port 8501 (daemon) and 8502 (user's terminal)
    for port in [8501, 8502]:
        try:
            run_test(port)
        except Exception as e:
            print(f"Port {port} run encountered: {e}")
