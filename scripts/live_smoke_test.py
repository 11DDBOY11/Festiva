#!/usr/bin/env python3
"""Live production smoke test script for Festiva AI."""

import json
import sys
import time
import urllib.error
import urllib.request

BACKEND_URL = "https://festiva-backend-g46c.onrender.com"
FRONTEND_URL = "https://festiva-frontend.onrender.com"


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def check_url(url: str, timeout: int = 40) -> tuple[int, str]:
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
        return 0, str(e)


def post_json(url: str, data: dict, token: str | None = None, timeout: int = 40) -> tuple[int, dict]:
    payload = json.dumps(data).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Festiva-Smoke-Test/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}
    except Exception as e:
        return 0, {"error": str(e)}


def get_json(url: str, token: str | None = None, timeout: int = 40) -> tuple[int, dict]:
    headers = {
        "User-Agent": "Festiva-Smoke-Test/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}
    except Exception as e:
        return 0, {"error": str(e)}


def run_smoke_test():
    log("=== FESTIVA LIVE PRODUCTION SMOKE TEST ===")

    # 1. Frontend Check
    log(f"1. Checking Frontend static site: {FRONTEND_URL} ...")
    st, body = check_url(FRONTEND_URL)
    log(f"   Frontend Status: {st}")
    assert st == 200, f"Frontend returned status {st}"
    assert "<!doctype html>" in body.lower() or "<html" in body.lower(), "Frontend missing HTML structure"
    log("   -> FRONTEND OK")

    # 2. Backend Health
    log(f"2. Checking Backend health: {BACKEND_URL}/health ...")
    st, body = check_url(f"{BACKEND_URL}/health")
    log(f"   Backend Health Status: {st}")
    assert st == 200, f"Backend health returned status {st}"
    log("   -> BACKEND HEALTH OK")

    # 3. Backend Health / Readiness (DB connection)
    log(f"3. Checking Backend health/ready: {BACKEND_URL}/health/ready ...")
    st, body = check_url(f"{BACKEND_URL}/health/ready")
    log(f"   Backend Readiness Status: {st}")
    assert st == 200, f"Backend readiness returned status {st}"
    log("   -> BACKEND READINESS OK")

    # 4. Public Demo Login
    log(f"4. Testing Public Demo Login: {BACKEND_URL}/auth/login with demo@festiva.ai ...")
    st, data = post_json(f"{BACKEND_URL}/auth/login", {"email": "demo@festiva.ai", "password": "DemoFestiva2026!"})
    log(f"   Demo Login Status: {st}")
    assert st == 200, f"Demo login returned status {st}: {data}"
    access_token = data.get("access_token")
    assert access_token, "No access token in response"
    log(f"   Authenticated as: {data.get('user', {}).get('email')}")
    log("   -> DEMO LOGIN OK")

    # 5. List Events
    log(f"5. Testing Event Listing: {BACKEND_URL}/events ...")
    st, events = get_json(f"{BACKEND_URL}/events", token=access_token)
    log(f"   Events List Status: {st}")
    assert st == 200, f"List events returned status {st}"
    assert isinstance(events, list), f"Expected list of events, got {type(events)}"
    log(f"   Retrieved {len(events)} events for user.")
    log("   -> LIST EVENTS OK")

    # 6. Fetch Plan for first event
    if events:
        first_event = events[0]
        event_id = first_event["id"]
        log(f"6. Testing Plan Fetch for event {event_id} ({first_event.get('title')}) ...")
        st, plan = get_json(f"{BACKEND_URL}/events/{event_id}/plan", token=access_token)
        log(f"   Plan Fetch Status: {st}")
        assert st == 200, f"Plan fetch returned status {st}"
        plan_content = plan.get("plan", plan)
        assert "budget" in plan_content, "Plan response missing budget"
        assert "timeline" in plan_content, "Plan response missing timeline"
        log(f"   Plan v{plan.get('version')}: Total Budget = INR {float(plan_content.get('total_budget', 0)):,.0f}")
        log("   -> GET PLAN OK")

    log("=== ALL LIVE PRODUCTION SMOKE TESTS PASSED! ===")


if __name__ == "__main__":
    try:
        run_smoke_test()
    except AssertionError as e:
        log(f"[SMOKE TEST FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        log(f"[SMOKE TEST ERROR] {e}")
        sys.exit(2)
