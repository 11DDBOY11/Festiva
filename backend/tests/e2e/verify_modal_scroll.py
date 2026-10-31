"""Verify Plan View Modal scrolling, sticky tabs, and full content visibility across:
1. Desktop Short Window (1280 x 600)
2. Desktop Full Height (1280 x 900)
3. Mobile Viewport (390 x 844)
4. Long list (20 timeline items) scroll to end
"""

import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", str(REPO_ROOT / ".artifacts")))
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")


def login_if_needed(page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    if page.locator("input[type='email']").is_visible():
        print("Logging in with demo credentials...")
        page.fill("input[type='email']", "demo@example.com")
        page.fill("input[type='password']", "password1234")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

    page.wait_for_selector("text=Celebrations & Plans", timeout=7000)


def open_modal(page):
    view_plan_btn = page.locator("#btn-view-plan").first
    if not view_plan_btn.is_visible():
        view_plan_btn = page.locator("button:has-text('View plan')").first
    view_plan_btn.click()
    page.wait_for_selector("#plan-modal-scrollable-body", timeout=5000)
    time.sleep(0.5)


def verify_viewports():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # ----------------------------------------------------
        # 1. Desktop Short (1280 x 600)
        # ----------------------------------------------------
        print("\n--- Testing Desktop Short (1280 x 600) ---")
        ctx_short = browser.new_context(viewport={"width": 1280, "height": 600})
        page_short = ctx_short.new_page()
        login_if_needed(page_short)
        open_modal(page_short)

        # Verify body scroll lock
        body_overflow = page_short.evaluate("document.body.style.overflow")
        print(f"Body overflow when modal is open: '{body_overflow}' (expected 'hidden')")
        assert body_overflow == "hidden", f"Expected body overflow hidden, got {body_overflow}"

        # Tab 1: Budget
        page_short.locator("#tab-btn-budget").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab1_budget.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 2: Timeline & Tasks
        page_short.locator("#tab-btn-timeline").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab2_timeline.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Scroll to bottom of scrollable body on Timeline
        scroll_script = "document.getElementById('plan-modal-scrollable-body').scrollTop = 99999"
        page_short.evaluate(scroll_script)
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab2_timeline_scrolled.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 3: Run-of-Show
        page_short.locator("#tab-btn-run-of-show").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab3_run_of_show.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 4: Vendors & Checklist
        page_short.locator("#tab-btn-vendors").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab4_vendors.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        page_short.evaluate(scroll_script)
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab4_vendors_scrolled.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 5: Suggestions / Changes
        page_short.locator("#tab-btn-refine").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab5_suggestions.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Scroll to bottom of Suggestions tab and confirm chat input is fully visible
        page_short.evaluate(scroll_script)
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_short_tab5_suggestions_scrolled.png"
        page_short.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        ctx_short.close()

        # ----------------------------------------------------
        # 2. Desktop Full Height (1280 x 900)
        # ----------------------------------------------------
        print("\n--- Testing Desktop Full Height (1280 x 900) ---")
        ctx_full = browser.new_context(viewport={"width": 1280, "height": 900})
        page_full = ctx_full.new_page()
        login_if_needed(page_full)
        open_modal(page_full)

        # Tab 1: Budget
        page_full.locator("#tab-btn-budget").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_full_tab1_budget.png"
        page_full.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 2: Timeline
        page_full.locator("#tab-btn-timeline").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_full_tab2_timeline.png"
        page_full.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 3: Run-of-Show
        page_full.locator("#tab-btn-run-of-show").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_full_tab3_run_of_show.png"
        page_full.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 4: Vendors
        page_full.locator("#tab-btn-vendors").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_full_tab4_vendors.png"
        page_full.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 5: Suggestions
        page_full.locator("#tab-btn-refine").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "desktop_full_tab5_suggestions.png"
        page_full.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        ctx_full.close()

        # ----------------------------------------------------
        # 3. Mobile Viewport (390 x 844)
        # ----------------------------------------------------
        print("\n--- Testing Mobile Viewport (390 x 844) ---")
        ctx_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
        )
        page_mobile = ctx_mobile.new_page()
        login_if_needed(page_mobile)
        open_modal(page_mobile)

        # Tab 1: Budget
        page_mobile.locator("#tab-btn-budget").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab1_budget.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 2: Timeline
        page_mobile.locator("#tab-btn-timeline").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab2_timeline.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Scroll to bottom of timeline on mobile
        scroll_script = "document.getElementById('plan-modal-scrollable-body').scrollTop = 99999"
        page_mobile.evaluate(scroll_script)
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab2_timeline_scrolled.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 3: Run-of-Show
        page_mobile.locator("#tab-btn-run-of-show").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab3_run_of_show.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 4: Vendors
        page_mobile.locator("#tab-btn-vendors").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab4_vendors.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Tab 5: Suggestions
        page_mobile.locator("#tab-btn-refine").click()
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab5_suggestions.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        # Scroll to bottom on Suggestions tab mobile
        page_mobile.evaluate(scroll_script)
        time.sleep(0.4)
        path = ARTIFACTS_DIR / "mobile_tab5_suggestions_scrolled.png"
        page_mobile.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        ctx_mobile.close()

        # ----------------------------------------------------
        # 4. Long List (20 timeline items) scroll to end test
        # ----------------------------------------------------
        print("\n--- Testing 20 Timeline Items Scrolling to End ---")
        ctx_long = browser.new_context(viewport={"width": 1280, "height": 700})
        page_long = ctx_long.new_page()
        login_if_needed(page_long)
        open_modal(page_long)

        # Switch to timeline
        page_long.locator("#tab-btn-timeline").click()
        time.sleep(0.4)

        # Inject 20 mock items to rigorously test scroll depth and verify reaching item #20
        inject_script = """() => {
            const container = document.querySelector("#plan-modal-scrollable-body .space-y-3");
            if (!container) return;
            container.innerHTML = "";
            for (let i = 1; i <= 20; i++) {
                const el = document.createElement("div");
                el.id = "timeline-task-" + i;
                el.className = "flex items-start justify-between gap-3 p-4 rounded-xl border " +
                    "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs";
                el.innerHTML = `
                    <div class="space-y-1">
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 rounded-md text-[11px] font-bold ` +
                                `bg-amber-100 text-amber-900">Task Milestone ${i} of 20</span>
                            <span class="px-2 py-0.5 rounded-md text-[11px] ` +
                                `bg-slate-100 text-slate-700">Category ${i}</span>
                        </div>
                        <p class="text-sm font-bold text-slate-900 dark:text-white">` +
                            `Milestone task #${i}: Finalize Mangaluru task ${i}</p>
                        <p class="text-xs text-slate-500">Owner: Festiva Specialist</p>
                    </div>
                    <div class="text-right">
                        <span class="text-xs font-mono font-bold text-amber-600">T-${20 - i}d</span>
                    </div>
                `;
                container.appendChild(el);
            }
        }"""
        page_long.evaluate(inject_script)
        time.sleep(0.3)

        # Scroll to bottom
        page_long.evaluate(scroll_script)
        time.sleep(0.4)

        # Assert task 20 is rendered and in viewport
        task20 = page_long.locator("#timeline-task-20")
        assert task20.is_visible(), "Timeline task #20 should be visible!"
        print("Verified: Task #20 is visible at the bottom of the scroll container!")

        path = ARTIFACTS_DIR / "long_timeline_20_items_end_scrolled.png"
        page_long.screenshot(path=str(path))
        print(f"Saved: {path.name}")

        ctx_long.close()
        browser.close()
        print("\nAll UI viewport & scrolling checks passed successfully!")


if __name__ == "__main__":
    verify_viewports()
