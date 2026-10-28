"""Tests for Phase 5 Plan Refinement, Propose Change, Diff Engine, and Streaming Chat."""

from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, email: str = "phase5_user@example.com") -> dict[str, str]:
    """Helper to register/login a user and return the Authorization header."""
    client.post(
        "/auth/register",
        json={"name": "Phase 5 Tester", "email": email, "password": "password1234"},
    )
    res = client.post(
        "/auth/login",
        json={"email": email, "password": "password1234"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_propose_change_reduce_decor(client: TestClient) -> None:
    """Test proposing 'reduce décor by ₹10,000' produces structured diff and budget impact."""
    headers = _get_auth_headers(client, "propose_decor@example.com")

    # 1. Create wedding event with 15 lakh budget
    create_res = client.post(
        "/events/",
        json={
            "title": "Kodialbail Coastal Wedding",
            "event_type": "wedding",
            "event_date": "2026-12-10",
            "city": "Mangaluru",
            "guest_count": 250,
            "total_budget": 1500000.0,
        },
        headers=headers,
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    event_id = create_res.json()["id"]

    # 2. Propose change: "reduce décor by ₹10,000"
    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce décor by ₹10,000", "base_version": 1},
        headers=headers,
    )
    assert prop_res.status_code == status.HTTP_200_OK
    change_data = prop_res.json()

    assert change_data["status"] == "pending"
    assert change_data["base_version"] == 1
    assert Decimal(str(change_data["budget_impact"])) == Decimal("-10000.00")

    diff = change_data["diff"]
    assert "summary" in diff
    assert len(diff["category_changes"]) >= 1

    decor_change = next(
        (c for c in diff["category_changes"] if "decor" in c["category"].lower()), None
    )
    assert decor_change is not None
    assert Decimal(str(decor_change["delta"])) == Decimal("-10000.00")
    delta_check = Decimal(str(decor_change["old_amount"])) - Decimal(
        str(decor_change["new_amount"])
    )
    assert delta_check == Decimal("10000.00")
    assert Decimal(str(diff["new_total_budget"])) == Decimal("1490000.00")


def test_accept_change_creates_version_n_plus_1(client: TestClient) -> None:
    """Test accepting proposed change creates version N+1 and updates active event plan."""
    headers = _get_auth_headers(client, "accept_change@example.com")

    # 1. Create event
    create_res = client.post(
        "/events/",
        json={
            "title": "Kadri Wedding",
            "event_type": "wedding",
            "total_budget": 1000000.0,
            "guest_count": 200,
        },
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # 2. Propose reduction
    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce décor by ₹10,000", "base_version": 1},
        headers=headers,
    )
    change_id = prop_res.json()["id"]

    # 3. Accept change
    accept_res = client.post(
        f"/events/{event_id}/changes/{change_id}/accept",
        headers=headers,
    )
    assert accept_res.status_code == status.HTTP_200_OK
    new_plan_data = accept_res.json()

    assert new_plan_data["version"] == 2
    assert new_plan_data["created_by"] == "user"
    assert "decor" in new_plan_data["change_summary"].lower()

    # 4. Verify current_version on event updated to 2
    ev_res = client.get(f"/events/{event_id}", headers=headers)
    assert ev_res.json()["current_version"] == 2

    # 5. Verify plan versions list contains v1 and v2
    ver_res = client.get(f"/events/{event_id}/versions", headers=headers)
    assert ver_res.status_code == status.HTTP_200_OK
    versions_list = ver_res.json()
    assert len(versions_list) == 2
    assert versions_list[0]["version"] == 1
    assert versions_list[1]["version"] == 2


def test_reject_change_leaves_version_unchanged(client: TestClient) -> None:
    """Test rejecting proposed change marks it rejected and preserves existing version."""
    headers = _get_auth_headers(client, "reject_change@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "Birthday Party", "event_type": "birthday", "total_budget": 50000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 5000", "base_version": 1},
        headers=headers,
    )
    change_id = prop_res.json()["id"]

    # Reject change
    reject_res = client.post(
        f"/events/{event_id}/changes/{change_id}/reject",
        headers=headers,
    )
    assert reject_res.status_code == status.HTTP_200_OK
    assert reject_res.json()["status"] == "rejected"

    # Verify event version remains 1
    ev_res = client.get(f"/events/{event_id}", headers=headers)
    assert ev_res.json()["current_version"] == 1


def test_optimistic_locking_rebase_once(client: TestClient) -> None:
    """Test optimistic locking rebases against latest version if client was on stale base."""
    headers = _get_auth_headers(client, "rebase_user@example.com")

    # 1. Create event (v1)
    create_res = client.post(
        "/events/",
        json={"title": "Grand Wedding", "event_type": "wedding", "total_budget": 500000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # 2. Advance to v2
    client.post(f"/events/{event_id}/plan/generate", headers=headers)
    ev_res = client.get(f"/events/{event_id}", headers=headers)
    assert ev_res.json()["current_version"] == 2

    # 3. Propose change referencing stale base_version=1
    stale_prop = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 5000", "base_version": 1},
        headers=headers,
    )
    assert stale_prop.status_code == status.HTTP_200_OK
    # Should automatically rebase to current_version 2
    assert stale_prop.json()["base_version"] == 2


def test_chat_refinement_streaming(client: TestClient) -> None:
    """Test streaming chat endpoint emits text/event-stream chunks ending in [DONE]."""
    headers = _get_auth_headers(client, "chat_user@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "Beach Party", "event_type": "birthday", "total_budget": 60000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    with client.stream(
        "POST",
        f"/events/{event_id}/chat",
        json={"message": "Can you suggest ways to reduce décor costs?"},
        headers=headers,
    ) as response:
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]

        lines = [
            line if isinstance(line, str) else line.decode("utf-8")
            for line in response.iter_lines()
            if line
        ]
        assert len(lines) > 0
        assert any("data:" in line for line in lines)
        assert any("[DONE]" in line for line in lines)
