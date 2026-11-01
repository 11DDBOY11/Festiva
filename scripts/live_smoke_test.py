#!/usr/bin/env python3
"""Comprehensive live production smoke test script for Festiva AI.

Covers all routes touched by the refactoring pass against the LIVE backend:
- Frontend static site availability & HTML structure
- Backend health & readiness
- Public demo login (read-only verification without modifying demo event)
- Dynamic throwaway user registration & authentication
- Event creation from birthday brief
- Plan retrieval & validation
- Plan change proposal ('reduce décor by ₹10,000')
- Plan change acceptance (v2, budget total preserved)
- Localized vendor message drafting
- Plan PDF export verification (status 200, %PDF signature)
- Streaming chat endpoint with valid auth (SSE stream) and without auth (401)
- Object-level authorization: User B access on User A's event returns 404
- Event cleanup (deletion via DELETE /events/{event_id})
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_FRONTEND_URL = "https://festiva-frontend.onrender.com"
DEFAULT_BACKEND_URL = "https://festiva-backend-g46c.onrender.com"


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def check_url(url: str, timeout: int = 60, max_retries: int = 3) -> tuple[int, str]:
    for attempt in range(max_retries):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Festiva-Smoke-Test/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < max_retries - 1:
                log(f"   Waiting for cold start ({attempt+1}/{max_retries})...")
                time.sleep(5)
                continue
            return 0, str(e)
    return 0, "Max retries exceeded"


def request_http(
    url: str,
    method: str = "GET",
    data: dict | None = None,
    token: str | None = None,
    timeout: int = 40,
    raw_response: bool = False,
) -> tuple[int, dict | bytes]:
    headers = {
        "User-Agent": "Festiva-Smoke-Test/1.0",
    }
    payload = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(data).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            if raw_response:
                return resp.status, content
            try:
                return resp.status, json.loads(content.decode("utf-8"))
            except Exception:
                return resp.status, {"raw": content.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        err_body = e.read()
        if raw_response:
            return e.code, err_body
        try:
            return e.code, json.loads(err_body.decode("utf-8"))
        except Exception:
            return e.code, {"raw": err_body.decode("utf-8", errors="replace")}
    except Exception as e:
        return 0, {"error": str(e)}


def run_smoke_test(frontend_url: str, backend_url: str):
    log("=== FESTIVA LIVE PRODUCTION SMOKE TEST ===")
    log(f"Frontend Target: {frontend_url}")
    log(f"Backend Target:  {backend_url}")

    # 1. Frontend Check
    log(f"1. Checking Frontend static site: {frontend_url} ...")
    st, body = check_url(frontend_url)
    log(f"   Frontend Status: {st}")
    assert st == 200, f"Frontend returned status {st}"
    assert "<!doctype html>" in body.lower() or "<html" in body.lower(), "Frontend missing HTML structure"
    log("   -> FRONTEND OK")

    # 2. Backend Health
    log(f"2. Checking Backend health: {backend_url}/health ...")
    st, body = check_url(f"{backend_url}/health")
    log(f"   Backend Health Status: {st}")
    assert st == 200, f"Backend health returned status {st}"
    log("   -> BACKEND HEALTH OK")

    # 3. Backend Health / Readiness (DB connection)
    log(f"3. Checking Backend readiness: {backend_url}/health/ready ...")
    st, body = check_url(f"{backend_url}/health/ready")
    log(f"   Backend Readiness Status: {st}")
    assert st == 200, f"Backend readiness returned status {st}"
    log("   -> BACKEND READINESS OK")

    # 4. Public Demo Account Login (Read-only verification)
    log(f"4. Testing Demo Login: {backend_url}/auth/login (demo@festiva.ai) ...")
    st, data = request_http(
        f"{backend_url}/auth/login",
        method="POST",
        data={"email": "demo@festiva.ai", "password": "DemoFestiva2026!"},
    )
    log(f"   Demo Login Status: {st}")
    assert st == 200, f"Demo login returned status {st}: {data}"
    demo_token = data.get("access_token")
    assert demo_token, "No access token in demo login response"

    # Verify demo event exists and is Plan v2
    st, demo_events = request_http(f"{backend_url}/events/", method="GET", token=demo_token)
    assert st == 200 and isinstance(demo_events, list) and len(demo_events) > 0, "No demo events returned"
    log(f"   Demo Account Events: {len(demo_events)} seeded event(s). Preserving untouched.")
    log("   -> DEMO LOGIN & SEED VERIFICATION OK")

    # 5. Register Throwaway User A
    rand_id = uuid.uuid4().hex[:8]
    user_a_email = f"smoketest_a_{rand_id}@festiva.example.com"
    user_a_pwd = f"SmokePass_{rand_id}!2026"
    log(f"5. Registering throwaway User A: {user_a_email} ...")
    st, reg_a = request_http(
        f"{backend_url}/auth/register",
        method="POST",
        data={"email": user_a_email, "password": user_a_pwd, "name": f"Smoke Tester A {rand_id}"},
    )
    assert st == 201, f"Registration of User A failed with status {st}: {reg_a}"

    # Log in as User A
    st, login_a = request_http(
        f"{backend_url}/auth/login",
        method="POST",
        data={"email": user_a_email, "password": user_a_pwd},
    )
    assert st == 200, f"Login as User A failed: {login_a}"
    token_a = login_a.get("access_token")
    assert token_a, "Missing token for User A"
    log("   -> USER A REGISTER & LOGIN OK")

    # 6. Create Event from Birthday Brief as User A
    log("6. Creating 50th Birthday Event for User A ...")
    event_payload = {
        "title": f"50th Birthday Milestone Celebration ({rand_id})",
        "event_type": "birthday",
        "event_date": "2027-03-20",
        "city": "Mangaluru",
        "guest_count": 80,
        "total_budget": 300000.0,
        "currency": "INR",
    }
    st, event_a = request_http(f"{backend_url}/events/", method="POST", data=event_payload, token=token_a)
    assert st == 201, f"Create event failed with status {st}: {event_a}"
    event_id = event_a.get("id")
    assert event_id, "Created event has no ID"
    log(f"   Created Event ID: {event_id} (Version: {event_a.get('current_version')})")
    log("   -> CREATE EVENT OK")

    try:
        # 7. Fetch Plan v1
        log(f"7. Fetching initial Plan v1 for event {event_id} ...")
        st, plan_v1_resp = request_http(f"{backend_url}/events/{event_id}/plan", method="GET", token=token_a)
        assert st == 200, f"Plan fetch failed: {plan_v1_resp}"
        assert plan_v1_resp.get("version") == 1, f"Expected version 1, got {plan_v1_resp.get('version')}"
        p_dict = plan_v1_resp.get("plan", {})
        assert "budget" in p_dict and "timeline" in p_dict, "Missing budget or timeline in plan"
        initial_total = float(p_dict.get("total_budget", 0))
        log(f"   Plan v1 loaded. Total Budget: INR {initial_total:,.0f}")
        log("   -> FETCH PLAN v1 OK")

        # 8. Propose Change: "reduce décor by ₹10,000"
        log("8. Proposing change: 'reduce décor by ₹10,000' ...")
        propose_payload = {"prompt": "reduce décor by ₹10,000", "base_version": 1}
        st, prop_resp = request_http(
            f"{backend_url}/events/{event_id}/changes/propose",
            method="POST",
            data=propose_payload,
            token=token_a,
        )
        assert st == 200, f"Propose change failed with status {st}: {prop_resp}"
        change_id = prop_resp.get("id")
        assert change_id, f"Proposed change missing ID: {prop_resp}"
        log(f"   Proposed Change ID: {change_id} (Status: {prop_resp.get('status')})")
        log("   -> PROPOSE CHANGE OK")

        # 9. Accept Change -> Version increments to v2, budget total unchanged
        log(f"9. Accepting proposed change {change_id} ...")
        st, accept_resp = request_http(
            f"{backend_url}/events/{event_id}/changes/{change_id}/accept",
            method="POST",
            token=token_a,
        )
        assert st == 200, f"Accept change failed with status {st}: {accept_resp}"
        assert accept_resp.get("version") == 2, f"Expected plan version 2, got {accept_resp.get('version')}"
        v2_total = float(accept_resp.get("plan", {}).get("total_budget", 0))
        assert abs(v2_total - initial_total) < 0.01, (
            f"Expected total budget unchanged ({initial_total}), got {v2_total}"
        )
        log(f"   Plan incremented to v2. Total Budget preserved: INR {v2_total:,.0f}")
        log("   -> ACCEPT CHANGE OK")

        # 10. Draft Vendor Message
        log("10. Drafting localized vendor inquiry for Catering ...")
        draft_payload = {
            "vendor_category": "Catering",
            "vendor_name": "Mangaluru Coastal Feasts",
            "custom_notes": "Please include traditional Coastal Mangalorean items and check vegetarian options.",
        }
        st, draft_resp = request_http(
            f"{backend_url}/events/{event_id}/messages/draft",
            method="POST",
            data=draft_payload,
            token=token_a,
        )
        assert st == 200, f"Draft vendor message failed with status {st}: {draft_resp}"
        assert draft_resp.get("vendor_category") == "Catering", "Mismatch in drafted category"
        msg_text = draft_resp.get("full_message") or draft_resp.get("subject", "")
        assert len(msg_text) > 20, f"Drafted message is unexpectedly short: {draft_resp}"
        log(f"    Vendor inquiry draft generated successfully ({len(msg_text)} chars).")
        log("   -> VENDOR MESSAGE DRAFT OK")

        # 11. Export Plan as PDF
        log(f"11. Exporting Plan PDF for event {event_id} ...")
        st, pdf_bytes = request_http(
            f"{backend_url}/events/{event_id}/export.pdf",
            method="GET",
            token=token_a,
            raw_response=True,
        )
        assert st == 200, f"PDF export failed with status {st}"
        assert isinstance(pdf_bytes, bytes) and pdf_bytes.startswith(b"%PDF"), (
            f"PDF response does not start with %PDF magic header: {pdf_bytes[:20]}"
        )
        log(f"    PDF generated successfully ({len(pdf_bytes):,} bytes, starts with %PDF).")
        log("   -> PDF EXPORT OK")

        # 12. Streaming Chat: with auth (200 SSE stream) and without auth (401 Unauthorized)
        log("12. Testing chat endpoint auth & streaming ...")
        # Without auth: must return 401
        st_noauth, resp_noauth = request_http(
            f"{backend_url}/events/{event_id}/chat",
            method="POST",
            data={"message": "What should we do next?"},
            token=None,
        )
        assert st_noauth == 401, f"Expected 401 Unauthorized without token, got {st_noauth}: {resp_noauth}"
        log("    Unauthenticated chat request correctly rejected with 401.")

        # With auth: returns 200 text/event-stream
        st_auth, sse_bytes = request_http(
            f"{backend_url}/events/{event_id}/chat",
            method="POST",
            data={"message": "Suggest timing for dinner"},
            token=token_a,
            raw_response=True,
        )
        assert st_auth == 200, f"Expected 200 for authenticated chat, got {st_auth}"
        sse_text = sse_bytes.decode("utf-8", errors="replace")
        assert "data:" in sse_text, f"SSE stream missing 'data:' prefix: {sse_text[:100]}"
        log("    Authenticated chat streaming returned valid SSE chunks.")
        log("   -> CHAT STREAM & AUTH OK")

        # 13. Object-Level Authorization: Register User B and verify 404 on User A's event
        user_b_email = f"smoketest_b_{rand_id}@festiva.example.com"
        user_b_pwd = f"SmokePass_B_{rand_id}!2026"
        log(f"13. Registering User B ({user_b_email}) to verify cross-user isolation ...")
        st, _ = request_http(
            f"{backend_url}/auth/register",
            method="POST",
            data={"email": user_b_email, "password": user_b_pwd, "name": "Smoke Tester B"},
        )
        assert st == 201, "Failed to register User B"
        st, login_b = request_http(
            f"{backend_url}/auth/login",
            method="POST",
            data={"email": user_b_email, "password": user_b_pwd},
        )
        token_b = login_b.get("access_token")
        assert token_b, "Missing token for User B"

        # User B attempts to access User A's event -> Must return 404 (not 403 or 200)
        st_cross, resp_cross = request_http(
            f"{backend_url}/events/{event_id}/plan",
            method="GET",
            token=token_b,
        )
        assert st_cross == 404, f"Expected 404 for User B accessing User A's plan, got {st_cross}: {resp_cross}"
        log("    User B accessing User A's event correctly received 404 Not Found.")
        log("   -> OBJECT-LEVEL AUTHORIZATION OK")

    finally:
        # 14. Cleanup: Delete test event as User A
        log(f"14. Cleaning up test event {event_id} ...")
        st_del, del_resp = request_http(
            f"{backend_url}/events/{event_id}",
            method="DELETE",
            token=token_a,
        )
        if st_del in (200, 204):
            log("    Test event deleted successfully.")
        else:
            log(f"    Warning: Test event deletion returned status {st_del}: {del_resp}")

    log("=== ALL LIVE PRODUCTION SMOKE TESTS PASSED! ===")


if __name__ == "__main__":
    frontend = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FRONTEND_URL
    backend = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BACKEND_URL
    try:
        run_smoke_test(frontend_url=frontend, backend_url=backend)
    except AssertionError as e:
        log(f"[SMOKE TEST FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        log(f"[SMOKE TEST ERROR] {e}")
        sys.exit(2)
