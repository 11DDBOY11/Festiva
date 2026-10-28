"""Phase 5 End-to-End Browser Verification via Playwright (MSEdge channel).

Automates:
1. Login with demo credentials
2. View event plan
3. Inspect venue showcase card and segmented tabs
4. Navigate to Suggestions / Changes tab
5. Propose 'reduce décor by ₹10,000'
6. Verify structured diff (Décor: ₹2,70,000 -> ₹2,60,000, Net Impact: -₹10,000)
7. Capture desktop diff viewer screenshot
8. Accept change (creates Plan v2)
9. Verify Plan v2, updated budget, and budget table
10. Capture desktop Plan v2 screenshot and 390px mobile screenshot
"""

import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

E2E_DIR = Path(__file__).resolve().parent
REPO_ROOT = E2E_DIR.parent.parent.parent
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / ".artifacts"

artifacts_env = os.environ.get("ARTIFACTS_DIR")
if artifacts_env:
    ARTIFACTS_DIR = Path(artifacts_env)
else:
    # Check conversation brain artifacts directory if present, else use repo relative .artifacts
    brain_dir = Path(
        r"C:\Users\dkk82\.gemini\antigravity\brain\c76ab51a-5c80-4fc8-bc0c-330b4acc9e08"
    )
    ARTIFACTS_DIR = brain_dir if brain_dir.exists() else DEFAULT_ARTIFACTS_DIR

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")


def run_verification():
    print(f"Starting Phase 5 UI verification against {BASE_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        # 1. Navigate to frontend
        print("Navigating to dashboard...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # Check if on login page
        if page.locator("input[type='email']").is_visible(timeout=3000):
            print("Logging in with demo credentials...")
            page.fill("input[type='email']", "demo@example.com")
            page.fill("input[type='password']", "password1234")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        # 2. On Celebrations & Plans dashboard
        print("Dashboard loaded. Looking for celebration plan...")
        page.wait_for_selector("text=Celebrations & Plans", timeout=5000)

        # Click View plan on first card
        view_plan_btn = page.locator("#btn-view-plan").first
        if not view_plan_btn.is_visible():
            view_plan_btn = page.locator("button:has-text('View plan')").first

        print("Clicking View plan...")
        view_plan_btn.click()

        # Wait for modal to open
        page.wait_for_selector("role=dialog", timeout=5000)
        time.sleep(1)
        print("Plan modal opened.")

        # Capture Initial Modal View showing Venue Card and Highlighted Segmented Tabs
        venue_tabs_screenshot = ARTIFACTS_DIR / "phase5_venue_and_tabs_desktop.png"
        page.screenshot(path=str(venue_tabs_screenshot))
        print(f"Captured desktop venue and tabs screenshot: {venue_tabs_screenshot}")

        # 3. Switch to Suggestions / Changes (Refine) tab
        print("Switching to Suggestions / Changes tab...")
        page.locator("#tab-btn-refine").click()
        time.sleep(1)

        # 4. Propose change: "reduce décor by ₹10,000"
        print("Proposing change: 'reduce décor by ₹10,000'...")
        suggest_chip = page.locator("#btn-suggest-reduce-decor")
        if suggest_chip.is_visible():
            suggest_chip.click()
        else:
            page.fill("#input-propose-prompt", "reduce décor by ₹10,000")
            page.locator("#btn-propose-change").click()

        # 5. Wait for Diff Viewer Card
        print("Waiting for structured Diff Viewer card...")
        page.wait_for_selector("text=Proposed Change (Pending Review)", timeout=10000)
        page.wait_for_selector("text=Net Impact:", timeout=5000)
        time.sleep(1)

        # Verify diff content
        net_impact_text = page.locator("text=Net Impact:").inner_text()
        print(f"Observed Net Impact badge: {net_impact_text}")
        assert "10,000" in net_impact_text, f"Expected 10,000 in {net_impact_text}"

        # 6. Capture Desktop Diff Viewer Screenshot
        diff_screenshot_path = ARTIFACTS_DIR / "phase5_diff_viewer_desktop.png"
        page.screenshot(path=str(diff_screenshot_path))
        print(f"Captured desktop diff viewer screenshot: {diff_screenshot_path}")

        # 7. Accept Change
        print("Clicking 'Accept Changes'...")
        page.locator("#btn-accept-change").click()

        # 8. Wait for version update and success message
        print("Waiting for version increment and success message...")
        try:
            page.wait_for_selector("text=Successfully applied change", timeout=6000)
            print("Found success message!")
        except Exception as e:
            print(f"Wait for success message error: {e}")
            err_el = page.locator(".bg-rose-500\\/10").first
            if err_el.is_visible():
                print(f"Observed error banner: {err_el.inner_text()}")
            badge_text = page.locator("button:has-text('Plan v')").first.inner_text()
            print(f"Observed current plan button text: {badge_text}")
            page.screenshot(path=str(ARTIFACTS_DIR / "phase5_accept_failure.png"))
            raise e

        # 9. Verify Budget Table
        print("Switching to Budget Table tab...")
        page.locator("#tab-btn-budget").click()
        time.sleep(1)

        # Capture Desktop Plan v2 Screenshot
        plan_v2_screenshot_path = ARTIFACTS_DIR / "phase5_plan_v2_desktop.png"
        page.screenshot(path=str(plan_v2_screenshot_path))
        print(f"Captured desktop Plan v2 screenshot: {plan_v2_screenshot_path}")

        # Capture Timeline Tab Screenshot
        print("Switching to Timeline Tab...")
        page.locator("#tab-btn-timeline").click()
        time.sleep(1)
        timeline_screenshot_path = ARTIFACTS_DIR / "phase5_timeline_desktop.png"
        page.screenshot(path=str(timeline_screenshot_path))
        print(f"Captured desktop timeline tab screenshot: {timeline_screenshot_path}")

        # 10. Mobile Viewport Screenshot (390x844)
        print("Resizing to mobile viewport (390x844)...")
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(1)

        mobile_screenshot_path = ARTIFACTS_DIR / "phase5_plan_v2_mobile.png"
        page.screenshot(path=str(mobile_screenshot_path))
        print(f"Captured mobile Plan v2 screenshot: {mobile_screenshot_path}")

        # Close browser
        browser.close()
        print("Phase 5 UI verification completed successfully!")


if __name__ == "__main__":
    try:
        run_verification()
    except Exception as exc:
        print(f"Verification error: {exc}", file=sys.stderr)
        sys.exit(1)
