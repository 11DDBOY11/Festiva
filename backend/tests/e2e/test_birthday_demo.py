"""End-to-End Birthday Demo Verification via Playwright (MSEdge / Chromium).

Scenario:
1. User logs in / registers.
2. Creates event: 21st birthday party, Mangaluru, 80 people, ₹75k.
3. Generates and inspects Plan v1.
4. Refinement: "Rain is likely, make it weather-safe and reduce décor by ₹10,000".
5. Diff inspection: decor -₹10k -> Contingency +₹10k, total budget ₹75k preserved.
6. Accept proposal -> Plan v2 generated.
7. Draft caterer inquiry message via minimal draft_message tool.
8. Export PDF via GET /events/{id}/export.pdf, download and parse bytes.
9. Verify PDF: ₹ Unicode glyphs, Budget Table, Sample Data note.
10. Saves screenshots, exported PDF, and timings to artifacts directory.
"""

import os
import sys
import time
from pathlib import Path

import httpx
import pypdf
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

E2E_DIR = Path(__file__).resolve().parent
REPO_ROOT = E2E_DIR.parent.parent.parent

# Target artifacts directory
brain_dir = Path(r"C:\Users\dkk82\.gemini\antigravity\brain\c76ab51a-5c80-4fc8-bc0c-330b4acc9e08")
ARTIFACTS_DIR = brain_dir if brain_dir.exists() else (REPO_ROOT / ".artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def run_birthday_demo():
    timings = {}
    total_start = time.time()
    print("=" * 80)
    print("STARTING FULL BIRTHDAY DEMO END-TO-END VERIFICATION")
    print("=" * 80)

    # 1. Setup Demo User & Auth via API
    t0 = time.time()
    demo_email = f"demo_birthday_{int(time.time())}@festiva.ai"
    demo_pass = "FestivaBirthday2026!"
    demo_name = "Devraj Mangaluru"

    reg_res = httpx.post(
        f"{API_URL}/auth/register",
        json={"email": demo_email, "password": demo_pass, "name": demo_name},
        timeout=10,
    )
    if reg_res.status_code != 200:
        log_res = httpx.post(
            f"{API_URL}/auth/login",
            json={"email": demo_email, "password": demo_pass},
            timeout=10,
        )
        token = log_res.json()["access_token"]
    else:
        token = reg_res.json()["access_token"]

    auth_headers = {"Authorization": f"Bearer {token}"}
    timings["user_auth_ms"] = round((time.time() - t0) * 1000, 1)
    print(f"[STEP 1] User registered: {demo_email} ({timings['user_auth_ms']}ms)")

    # 2. Create the Birthday Event via API
    t0 = time.time()
    event_payload = {
        "title": "21st Birthday Party - Mangaluru Coastal Celebration",
        "event_type": "birthday",
        "event_date": "2026-11-20",
        "guest_count": 80,
        "total_budget": 75000.0,
        "location": "Mangaluru, Karnataka",
        "description": (
            "21st birthday party, Mangaluru, 80 people, ₹75,000, outdoor evening, "
            "vegetarian snacks, music, photo booth"
        ),
    }
    create_res = httpx.post(
        f"{API_URL}/events/",
        json=event_payload,
        headers=auth_headers,
        timeout=10,
    )
    assert create_res.status_code in (200, 201), f"Failed to create event: {create_res.text}"
    event_data = create_res.json()
    event_id = event_data["id"]
    timings["event_create_ms"] = round((time.time() - t0) * 1000, 1)
    print(f"[STEP 2] Event ID={event_id}, Budget=₹75k, Guests=80 ({timings['event_create_ms']}ms)")

    # 3. Launch Playwright Browser Session
    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 850})
        page = context.new_page()

        # Inject JWT auth token into localStorage
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.evaluate(
            """([token, user]) => {
                localStorage.setItem('festiva_access_token', token);
                localStorage.setItem('festiva_refresh_token', token);
            }""",
            [token, {"id": str(event_id), "email": demo_email, "name": demo_name}],
        )

        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)
        timings["browser_init_ms"] = round((time.time() - t0) * 1000, 1)
        print(f"[STEP 3] Browser initialized and logged in ({timings['browser_init_ms']}ms)")

        # 4. Open Plan View Modal (Plan v1)
        t0 = time.time()
        view_plan_btn = page.locator(f"#btn-view-plan-{event_id}")
        if not view_plan_btn.is_visible():
            view_plan_btn = page.locator("button:has-text('View plan')").first
        view_plan_btn.click()

        page.wait_for_selector("role=dialog", timeout=6000)
        time.sleep(1.2)

        # Assert Sample Data badge exists on Venue Card
        assert page.locator("text=Sample Data").first.is_visible(), (
            "Sample Data badge should be visible on Venue card"
        )
        assert page.locator("text=₹75,000").first.is_visible(), (
            "Total budget ₹75,000 should be visible"
        )

        # Screenshot Step 1: Plan v1
        shot_v1 = ARTIFACTS_DIR / "demo_01_plan_v1.png"
        page.screenshot(path=str(shot_v1))
        timings["plan_v1_inspect_ms"] = round((time.time() - t0) * 1000, 1)
        print(f"[STEP 4] Plan v1 captured: {shot_v1.name} ({timings['plan_v1_inspect_ms']}ms)")

        # 5. Switch to Suggestions / Changes tab and Propose Weather-Safe + Decor Reduction
        t0 = time.time()
        page.locator("#tab-btn-refine").click()
        time.sleep(0.6)

        refine_prompt = "Rain is likely, make it weather-safe and reduce décor by ₹10,000"
        page.fill("#input-propose-prompt", refine_prompt)
        page.locator("#btn-propose-change").click()

        # Wait for diff proposal to render
        page.wait_for_selector("#btn-accept-change", timeout=12000)
        time.sleep(1)

        # Verify Diff content
        diff_text = page.locator("role=dialog").first.inner_text()
        assert "10,000" in diff_text, "Diff should show ₹10,000 change"
        assert page.locator("#btn-accept-change").is_visible()

        # Screenshot Step 2: Diff Proposal
        shot_diff = ARTIFACTS_DIR / "demo_02_diff_proposal.png"
        page.screenshot(path=str(shot_diff))
        timings["proposal_diff_ms"] = round((time.time() - t0) * 1000, 1)
        print(f"[STEP 5] Diff captured: {shot_diff.name} ({timings['proposal_diff_ms']}ms)")

        # 6. Accept Proposal -> Plan v2
        t0 = time.time()
        page.locator("#btn-accept-change").click()

        # Wait for Plan v2 badge or banner
        page.wait_for_selector("text=Plan v2", timeout=10000)
        time.sleep(1)

        # Switch to Budget Table tab to verify ₹10,000 reallocated to contingency
        page.locator("#tab-btn-budget").click()
        time.sleep(0.8)

        # Assert Contingency & Reserve line is visible with ₹10,000
        budget_table_text = page.locator("table").first.inner_text()
        assert "Contingency" in budget_table_text, (
            "Contingency row must be visible in Plan v2 budget table"
        )
        assert "10,000" in budget_table_text, "₹10,000 must be visible in Plan v2 budget table"
        assert "75,000" in budget_table_text, "Total budget ₹75,000 must remain unchanged"
        assert "_" not in budget_table_text, "No budget category should contain an underscore"

        # Screenshot Step 3: Plan v2
        shot_v2 = ARTIFACTS_DIR / "demo_03_plan_v2.png"
        page.screenshot(path=str(shot_v2))
        timings["plan_v2_accept_ms"] = round((time.time() - t0) * 1000, 1)
        print(f"[STEP 6] Plan v2 captured: {shot_v2.name} ({timings['plan_v2_accept_ms']}ms)")

        # 7. Go to Vendors & Checklist -> Click "Draft Message" on Caterer
        t0 = time.time()
        page.locator("#tab-btn-vendors").click()
        time.sleep(0.8)

        # Click first Draft Message button
        draft_btn = page.locator("#btn-draft-vendor-0")
        if not draft_btn.is_visible():
            draft_btn = page.locator("#btn-draft-chk-0")
        draft_btn.click()

        # Wait for Draft Message Dialog to appear
        page.wait_for_selector("#btn-copy-draft-message", timeout=12000)
        time.sleep(1)

        dialog_text = page.locator("role=dialog").last.inner_text()
        assert "80" in dialog_text, "Draft message should reference 80 guests"
        assert "Draft Vendor Inquiry" in dialog_text

        # Screenshot Step 4: Draft Message Dialog
        shot_draft = ARTIFACTS_DIR / "demo_04_draft_message_dialog.png"
        page.screenshot(path=str(shot_draft))
        timings["draft_message_ms"] = round((time.time() - t0) * 1000, 1)
        print(
            f"[STEP 7] Draft message captured: {shot_draft.name} ({timings['draft_message_ms']}ms)"
        )

        # Close Draft Dialog
        page.locator("button:has-text('Close')").last.click()
        time.sleep(0.5)

        # 8. Export PDF and Save to Artifacts
        t0 = time.time()
        pdf_res = httpx.get(
            f"{API_URL}/events/{event_id}/export.pdf?version=2",
            headers=auth_headers,
            timeout=15,
        )
        assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.status_code}"
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert len(pdf_res.content) > 1000, "PDF size must be > 1KB"

        pdf_path = ARTIFACTS_DIR / "demo_birthday_plan_v2.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_res.content)
        timings["pdf_export_ms"] = round((time.time() - t0) * 1000, 1)
        print(
            f"[STEP 8] Exported PDF saved: {pdf_path.name} "
            f"({len(pdf_res.content)} bytes, {timings['pdf_export_ms']}ms)"
        )

        browser.close()

    # 9. Parse and Validate Exported PDF Content
    t0 = time.time()
    reader = pypdf.PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    print("\n" + "=" * 80)
    print(f"EXPORTED PDF CONTENT INSPECTION ({num_pages} pages, {len(extracted_text)} chars)")
    print("=" * 80)

    # Assertions on PDF contents
    assert "₹" in extracted_text, "PDF must contain Unicode Indian Rupee symbol (₹)"
    assert "75,000" in extracted_text, "PDF must display total budget ₹75,000"
    assert "Plan Version 2" in extracted_text, "PDF must export Plan Version 2"
    assert "Contingency" in extracted_text, "PDF must include Contingency & Reserve line"
    assert "10,000" in extracted_text, "PDF must display ₹10,000 contingency allocation"
    assert "Decor_cake" not in extracted_text, "PDF must not contain raw key 'Decor_cake'"
    assert "Entertainment_photo" not in extracted_text, (
        "PDF must not contain raw key 'Entertainment_photo'"
    )
    assert "BUDGET BREAKDOWN" in extracted_text.upper(), "PDF must contain Budget Breakdown section"
    assert "TIMELINE" in extracted_text.upper(), "PDF must contain Timeline section"
    assert "RUN-OF-SHOW" in extracted_text.upper(), "PDF must contain Run-of-Show section"
    assert "SAMPLE DATA" in extracted_text.upper() or "DEMONSTRATION" in extracted_text.upper(), (
        "PDF must contain sample data / demonstration note for sample vendors"
    )

    # Print representative excerpts from PDF
    sections = [
        "PLAN OVERVIEW",
        "1. BUDGET BREAKDOWN",
        "2. TIMELINE & MILESTONES",
        "SAMPLE DATA",
    ]
    for section_title in sections:
        pos = extracted_text.upper().find(section_title)
        if pos != -1:
            snippet = extracted_text[pos : pos + 350].strip()
            print(f"\n--- [PDF EXCERPT: {section_title}] ---\n{snippet}\n")

    timings["pdf_verify_ms"] = round((time.time() - t0) * 1000, 1)
    timings["total_demo_sec"] = round(time.time() - total_start, 2)

    print("=" * 80)
    print("DEMO EXECUTION TIMINGS BENCHMARK:")
    for k, v in timings.items():
        print(f"  - {k}: {v}")
    print("=" * 80)
    print("[SUCCESS] Full Birthday Demo end-to-end completed with 100% assertions passing.")
    return timings, pdf_path


if __name__ == "__main__":
    run_birthday_demo()
