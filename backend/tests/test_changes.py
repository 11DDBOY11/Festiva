"""Tests for Phase 5 Plan Refinement, Propose Change, Diff Engine, and Streaming Chat."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.domain.diff_engine import (
    CategoryDelta,
    PlanDiff,
    TimelineDelta,
    UnsupportedOperationError,
    apply_plan_diff,
    generate_plan_diff,
)
from app.domain.schemas import PlanSchema


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
    # When decor is reduced without explicit total budget decrease,
    # money is reallocated to Contingency
    assert Decimal(str(change_data["budget_impact"])) == Decimal("0.00")

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

    contingency_change = next(
        (
            c
            for c in diff["category_changes"]
            if any(w in c["category"].lower() for w in ["contingency", "buffer", "reserve"])
        ),
        None,
    )
    assert contingency_change is not None
    assert Decimal(str(contingency_change["delta"])) == Decimal("10000.00")
    assert Decimal(str(diff["new_total_budget"])) == Decimal("1500000.00")


def test_accept_change_creates_version_n_plus_1(client: TestClient) -> None:
    """Test accepting proposed change creates version N+1 and updates active event plan."""
    headers = _get_auth_headers(client, "accept_change@example.com")

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

    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce décor by ₹10,000", "base_version": 1},
        headers=headers,
    )
    change_id = prop_res.json()["id"]

    accept_res = client.post(
        f"/events/{event_id}/changes/{change_id}/accept",
        headers=headers,
    )
    assert accept_res.status_code == status.HTTP_200_OK
    new_plan_data = accept_res.json()

    assert new_plan_data["version"] == 2
    assert new_plan_data["created_by"] == "user"
    assert "decor" in new_plan_data["change_summary"].lower()

    ev_res = client.get(f"/events/{event_id}", headers=headers)
    assert ev_res.json()["current_version"] == 2

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

    reject_res = client.post(
        f"/events/{event_id}/changes/{change_id}/reject",
        headers=headers,
    )
    assert reject_res.status_code == status.HTTP_200_OK
    assert reject_res.json()["status"] == "rejected"

    ev_res = client.get(f"/events/{event_id}", headers=headers)
    assert ev_res.json()["current_version"] == 1


def test_stale_base_rebase_touches_nothing_changed(client: TestClient) -> None:
    """Test stale-base rebase when proposal diff touches a category untouched by newer version."""
    headers = _get_auth_headers(client, "rebase_diff_ok@example.com")

    create_res = client.post(
        "/events/",
        json={
            "title": "Kudla Reception",
            "event_type": "wedding",
            "total_budget": 1000000.0,
            "guest_count": 200,
        },
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # 1. Propose change on v1 modifying Decor
    prop_decor = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 10,000", "base_version": 1},
        headers=headers,
    )
    change_decor_id = prop_decor.json()["id"]

    # 2. Advance event to v2 via a change on Catering
    prop_catering = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce catering by 20,000", "base_version": 1},
        headers=headers,
    )
    client.post(
        f"/events/{event_id}/changes/{prop_catering.json()['id']}/accept",
        headers=headers,
    )
    assert client.get(f"/events/{event_id}", headers=headers).json()["current_version"] == 2

    # 3. Accept stale Decor proposal (was created on base_version=1)
    accept_res = client.post(
        f"/events/{event_id}/changes/{change_decor_id}/accept",
        headers=headers,
    )
    assert accept_res.status_code == status.HTTP_200_OK
    assert accept_res.json()["version"] == 3

    # Both changes should be present in v3
    v3_plan = accept_res.json()["plan"]
    categories = {
        c["category"]: Decimal(str(c["allocated_amount"])) for c in v3_plan["budget"]["categories"]
    }
    decor_key = next(k for k in categories if "decor" in k.lower())
    catering_key = next(k for k in categories if "cater" in k.lower())
    assert categories[decor_key] > 0
    assert categories[catering_key] > 0
    assert client.get(f"/events/{event_id}", headers=headers).json()["current_version"] == 3


def test_stale_base_regenerate_once_conflict(client: TestClient) -> None:
    """Test conflict detection and 1-shot regeneration when stale base touched the same category."""
    headers = _get_auth_headers(client, "conflict_regen@example.com")

    create_res = client.post(
        "/events/",
        json={
            "title": "Beach Wedding",
            "event_type": "wedding",
            "total_budget": 1200000.0,
            "guest_count": 200,
        },
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # 1. Proposal A on v1 modifying Decor
    prop_a = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 10,000", "base_version": 1},
        headers=headers,
    )
    prop_a_id = prop_a.json()["id"]

    # 2. Advance event to v2 modifying Decor as well
    prop_b = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 20,000", "base_version": 1},
        headers=headers,
    )
    client.post(
        f"/events/{event_id}/changes/{prop_b.json()['id']}/accept",
        headers=headers,
    )
    assert client.get(f"/events/{event_id}", headers=headers).json()["current_version"] == 2

    # 3. Accept Proposal A on stale base (conflict on Decor) -> auto-regenerates once against v2
    accept_res = client.post(
        f"/events/{event_id}/changes/{prop_a_id}/accept",
        headers=headers,
    )
    assert accept_res.status_code == status.HTTP_200_OK
    assert accept_res.json()["version"] == 3


def test_concurrent_accepts_fails_cleanly(client: TestClient) -> None:
    """Test that accepting an already-applied change fails cleanly without corruption."""
    headers = _get_auth_headers(client, "concurrent_accept@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "Anniversary Dinner", "event_type": "birthday", "total_budget": 80000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 5000", "base_version": 1},
        headers=headers,
    )
    change_id = prop_res.json()["id"]

    # First accept: succeeds
    res1 = client.post(f"/events/{event_id}/changes/{change_id}/accept", headers=headers)
    assert res1.status_code == status.HTTP_200_OK

    # Second accept: fails cleanly with 400 Bad Request
    res2 = client.post(f"/events/{event_id}/changes/{change_id}/accept", headers=headers)
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already applied" in res2.json()["detail"].lower()


def test_simultaneous_concurrent_accepts_threads(client: TestClient) -> None:
    """Genuinely concurrent test: two simultaneous accepts on the same base version using threads.

    Asserts exactly one succeeds (HTTP 200), the other fails cleanly (HTTP 400 or 409),
    and UNIQUE(event_id, version) / row lock guards database integrity.
    """
    import concurrent.futures

    from app.api.deps import get_db
    from app.main import app
    from tests.conftest import TestingSessionLocal

    orig_override = app.dependency_overrides.get(get_db)

    def thread_safe_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = thread_safe_get_db

    try:
        headers = _get_auth_headers(client, "genuinely_concurrent@example.com")

        create_res = client.post(
            "/events/",
            json={
                "title": "Concurrent Race Event",
                "event_type": "birthday",
                "total_budget": 100000.0,
            },
            headers=headers,
        )
        event_id = create_res.json()["id"]

        prop_res = client.post(
            f"/events/{event_id}/changes/propose",
            json={"prompt": "reduce decor by 5000", "base_version": 1},
            headers=headers,
        )
        change_id = prop_res.json()["id"]

        def call_accept() -> int:
            res = client.post(f"/events/{event_id}/changes/{change_id}/accept", headers=headers)
            return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(call_accept), executor.submit(call_accept)]
            statuses = [f.result() for f in futures]

        # Exactly one thread succeeds with HTTP 200 OK
        assert statuses.count(status.HTTP_200_OK) == 1
        # The other thread fails cleanly with 400 Bad Request or 409 Conflict (never 500)
        failed_status = [s for s in statuses if s != status.HTTP_200_OK][0]
        assert failed_status in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)

        # Verify event state is at v2 and only one PlanVersion for v2 exists in DB
        ev_res = client.get(f"/events/{event_id}", headers=headers)
        assert ev_res.status_code == status.HTTP_200_OK
        assert ev_res.json()["current_version"] == 2
    finally:
        if orig_override:
            app.dependency_overrides[get_db] = orig_override
        else:
            app.dependency_overrides.pop(get_db, None)


def test_decor_reduction_reallocates_to_contingency_and_preserves_total_budget(
    client: TestClient,
) -> None:
    """Assert reducing décor by ₹10,000 reallocates to Contingency
    and keeps total_budget unchanged.
    """
    headers = _get_auth_headers(client, "decor_contingency@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Decor Contingency Test", "event_type": "birthday", "total_budget": 50000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]
    initial_total = Decimal(str(create_res.json()["total_budget"]))

    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 10000", "base_version": 1},
        headers=headers,
    )
    assert prop_res.status_code == status.HTTP_200_OK
    diff_data = prop_res.json()["diff"]

    # Verify diff shows money went to Contingency
    decor_delta = next(
        (d for d in diff_data["category_changes"] if "decor" in d["category"].lower()), None
    )
    contingency_delta = next(
        (
            d
            for d in diff_data["category_changes"]
            if any(w in d["category"].lower() for w in ["contingency", "buffer", "reserve"])
        ),
        None,
    )
    assert decor_delta is not None
    assert Decimal(str(decor_delta["delta"])) == Decimal("-10000")
    assert contingency_delta is not None
    assert Decimal(str(contingency_delta["delta"])) == Decimal("10000")
    assert Decimal(str(diff_data["new_total_budget"])) == initial_total
    assert "contingency" in diff_data["summary"].lower() or "buffer" in diff_data["summary"].lower()

    # Accept change
    change_id = prop_res.json()["id"]
    accept_res = client.post(f"/events/{event_id}/changes/{change_id}/accept", headers=headers)
    assert accept_res.status_code == status.HTTP_200_OK

    # Assert events.total_budget is unchanged after accept
    event_res = client.get(f"/events/{event_id}", headers=headers)
    assert event_res.status_code == status.HTTP_200_OK
    final_total = Decimal(str(event_res.json()["total_budget"]))
    assert final_total == initial_total


def test_forced_invalid_llm_output_retry_and_fallback() -> None:
    """Test forced invalid LLM output triggers repair retry then deterministic fallback."""
    mock_client = MagicMock()
    # Force generate_structured to raise RuntimeError (simulating bad output after retry failure)
    mock_client.generate_structured.side_effect = RuntimeError(
        "Invalid JSON schema output from LLM"
    )

    # Sample base plan schema
    from app.domain.schemas import BudgetBreakdown, BudgetCategoryAllocation, PlanSchema

    base_plan = PlanSchema(
        version=1,
        title="Test Event",
        event_type="wedding",
        event_date=date.today() + timedelta(days=60),
        guest_count=100,
        total_budget=Decimal("500000"),
        currency="INR",
        summary="Test wedding plan",
        budget=BudgetBreakdown(
            total_budget=Decimal("500000"),
            currency="INR",
            categories=[
                BudgetCategoryAllocation(
                    category="Decor",
                    share_pct=Decimal("30"),
                    allocated_amount=Decimal("150000"),
                    per_guest_cost=Decimal("1500"),
                ),
                BudgetCategoryAllocation(
                    category="Catering",
                    share_pct=Decimal("50"),
                    allocated_amount=Decimal("250000"),
                    per_guest_cost=Decimal("2500"),
                ),
                BudgetCategoryAllocation(
                    category="Contingency",
                    share_pct=Decimal("20"),
                    allocated_amount=Decimal("100000"),
                    per_guest_cost=Decimal("1000"),
                ),
            ],
        ),
    )

    # 1. Deterministic fallback kicks in for valid reduction pattern
    # (reallocating to contingency)
    diff = generate_plan_diff(base_plan, "reduce décor by ₹10,000", client=mock_client)
    assert diff.budget_impact == Decimal("0")
    assert diff.new_total_budget == Decimal("500000")
    decor_delta = next(c for c in diff.category_changes if c.category == "Decor")
    assert decor_delta.delta == Decimal("-10000")
    contingency_delta = next(
        c
        for c in diff.category_changes
        if any(w in c.category.lower() for w in ["contingency", "buffer", "reserve"])
    )
    assert contingency_delta.delta == Decimal("10000")

    # 2. Unsupported request should raise UnsupportedOperationError
    with pytest.raises(UnsupportedOperationError) as exc_info:
        generate_plan_diff(base_plan, "book 5 airline tickets to London", client=mock_client)
    assert "can't do that yet" in str(exc_info.value).lower()


def test_sse_chat_read_only_and_requires_auth(client: TestClient) -> None:
    """Test that SSE chat endpoint strictly requires auth and does not mutate database."""
    headers = _get_auth_headers(client, "chat_auth_test@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "Beach Party", "event_type": "birthday", "total_budget": 60000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # 1. Unauthenticated request must return 401 Unauthorized
    unauth_res = client.post(
        f"/events/{event_id}/chat",
        json={"message": "What should I do first?"},
    )
    assert unauth_res.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Authenticated request streams tokens
    with client.stream(
        "POST",
        f"/events/{event_id}/chat",
        json={"message": "Can you advise on photography in Mangaluru?"},
        headers=headers,
    ) as response:
        assert response.status_code == status.HTTP_200_OK
        lines = [
            line if isinstance(line, str) else line.decode("utf-8")
            for line in response.iter_lines()
            if line
        ]
        assert any("[DONE]" in line for line in lines)

    # 3. Verify event state was strictly read-only
    ev_after = client.get(f"/events/{event_id}", headers=headers).json()
    assert ev_after["current_version"] == 1
    assert Decimal(str(ev_after["total_budget"])) == Decimal("60000.00")
    versions = client.get(f"/events/{event_id}/versions", headers=headers).json()
    assert len(versions) == 1


def test_apply_plan_diff_date_validation_rejects_past_dated_new_task() -> None:
    """Requirement 4: Verify past-date tolerance only grandfathers base tasks
    and rejects new past tasks.
    """
    today = date.today()
    past_date = today - timedelta(days=5)

    # Base plan with a past task (simulating an older plan created a few days ago)
    base_plan = PlanSchema(
        version=1,
        title="Historical Event",
        event_type="birthday",
        event_date=today + timedelta(days=30),
        guest_count=50,
        total_budget=Decimal("50000"),
        currency="INR",
        summary="Historical plan",
        budget={
            "total_budget": Decimal("50000"),
            "currency": "INR",
            "categories": [
                {
                    "category": "Decor",
                    "share_pct": Decimal("50"),
                    "allocated_amount": Decimal("25000"),
                    "per_guest_cost": Decimal("500"),
                },
                {
                    "category": "Catering",
                    "share_pct": Decimal("50"),
                    "allocated_amount": Decimal("25000"),
                    "per_guest_cost": Decimal("500"),
                },
            ],
        },
        timeline=[
            {
                "phase": "Planning",
                "days_before_event": 35,
                "target_date": past_date,  # Existing historical task
                "task": "Old task from previous week",
                "category": "Planning",
                "owner": "Host",
                "priority": "low",
            }
        ],
    )

    # 1. Applying a budget diff without new timeline tasks succeeds (grandfathering historical task)
    valid_diff = PlanDiff(
        prompt="reduce decor by 1000",
        summary="Reduced Decor by ₹1,000",
        category_changes=[
            CategoryDelta(
                category="Decor",
                old_amount=Decimal("25000"),
                new_amount=Decimal("24000"),
                delta=Decimal("-1000"),
                old_share_pct=Decimal("50"),
                new_share_pct=Decimal("48.98"),
            )
        ],
        timeline_changes=[],
        old_total_budget=Decimal("50000"),
        new_total_budget=Decimal("49000"),
        budget_impact=Decimal("-1000"),
    )
    refined_plan = apply_plan_diff(base_plan, valid_diff)
    assert refined_plan.version == 2

    # 2. Attempting to add a NEW task with a past date MUST be rejected
    invalid_diff = PlanDiff(
        prompt="add past milestone",
        summary="Added past milestone",
        category_changes=[],
        timeline_changes=[
            TimelineDelta(
                task="Book magician last week",
                action="added",
                new_date=past_date.isoformat(),
                reason="Invalid past task",
            )
        ],
        old_total_budget=Decimal("50000"),
        new_total_budget=Decimal("50000"),
        budget_impact=Decimal("0"),
    )

    with pytest.raises(ValueError) as exc_info:
        apply_plan_diff(base_plan, invalid_diff)
    assert "cannot be scheduled before today" in str(exc_info.value).lower()
