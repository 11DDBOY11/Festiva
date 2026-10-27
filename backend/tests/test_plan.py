"""Tests for Phase 4 Plan Generation and Plan API endpoints."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient

from app.domain.checklist import get_checklist_for_event, get_run_of_show_for_event
from app.domain.plan_generator import generate_plan
from app.domain.timeline import generate_timeline
from app.domain.validators import (
    validate_plan_budget,
    validate_plan_dates,
    validate_price_honesty,
    validate_vendor_grounding,
)
from app.domain.vendor_directory import get_known_vendor_ids, get_known_vendor_map


def _get_auth_headers(client: TestClient, email: str = "plan_user@example.com") -> dict[str, str]:
    """Helper to register/login a user and return the Authorization header."""
    client.post(
        "/auth/register",
        json={"name": "Plan Tester", "email": email, "password": "password1234"},
    )
    res = client.post(
        "/auth/login",
        json={"email": email, "password": "password1234"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_plan_wedding_integrity() -> None:
    """Test deterministic wedding plan generation adheres to all domain rules."""
    today = date.today()
    event_date = today + timedelta(days=120)
    budget = Decimal("1500000.00")
    guests = 300

    plan = generate_plan(
        event_type="wedding",
        total_budget=budget,
        event_date=event_date,
        guest_count=guests,
        city="Mangaluru",
        reference_today=today,
    )

    assert plan.version == 1
    assert plan.total_budget == budget
    assert plan.guest_count == guests
    assert len(plan.timeline) > 0
    assert len(plan.checklist) > 0
    assert len(plan.run_of_show) > 0
    assert len(plan.vendor_shortlist) > 0

    # Validators
    budget_ok, b_msg = validate_plan_budget(plan)
    assert budget_ok, b_msg

    dates_ok, d_msg = validate_plan_dates(plan, reference_today=today)
    assert dates_ok, d_msg

    grounding_ok, g_msgs = validate_vendor_grounding(plan, get_known_vendor_ids())
    assert grounding_ok, g_msgs

    honesty_ok, h_msgs = validate_price_honesty(plan, get_known_vendor_map())
    assert honesty_ok, h_msgs


def test_generate_plan_birthday_and_community() -> None:
    """Test birthday and community event generation."""
    today = date.today()

    b_plan = generate_plan(
        event_type="birthday",
        total_budget=Decimal("80000.00"),
        event_date=today + timedelta(days=30),
        guest_count=40,
        reference_today=today,
    )
    assert b_plan.event_type == "birthday"
    assert b_plan.budget.allocated_sum == Decimal("80000.00")

    c_plan = generate_plan(
        event_type="community",
        total_budget=Decimal("250000.00"),
        event_date=today + timedelta(days=45),
        guest_count=500,
        reference_today=today,
    )
    assert c_plan.event_type == "community"
    assert c_plan.budget.allocated_sum == Decimal("250000.00")


def test_timeline_ordering_and_clamping() -> None:
    """Verify timeline milestones are strictly sorted and clamped between today and event_date."""
    today = date.today()
    # Short notice event (3 days away)
    event_date = today + timedelta(days=3)

    timeline = generate_timeline("wedding", event_date=event_date, reference_today=today)
    assert len(timeline) > 0

    prev_date = today
    for item in timeline:
        assert item.target_date is not None
        assert item.target_date >= today
        assert item.target_date <= event_date
        assert item.target_date >= prev_date
        prev_date = item.target_date


def test_checklist_and_run_of_show_templates() -> None:
    """Verify regional checklist questions and run of show hourly slots."""
    checklist = get_checklist_for_event("wedding")
    assert any("Mangaluru" in q.item or "Mangalorean" in q.item for q in checklist)
    assert all(len(q.questions_to_ask_vendor) > 0 for q in checklist)

    ros = get_run_of_show_for_event("wedding")
    assert len(ros) >= 5
    assert any("Muhurtham" in s.activity for s in ros)


def test_event_plan_endpoints(client: TestClient) -> None:
    """Test GET and POST /events/{id}/plan API endpoints."""
    headers = _get_auth_headers(client, "plan_api_tester@example.com")

    # 1. Create event with budget
    create_res = client.post(
        "/events/",
        json={
            "title": "Grand Coastal Reception",
            "event_type": "wedding",
            "event_date": "2026-11-20",
            "city": "Mangaluru",
            "guest_count": 200,
            "total_budget": 1200000.0,
        },
        headers=headers,
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    event_data = create_res.json()
    event_id = event_data["id"]
    assert event_data["current_version"] == 1

    # 2. Get Plan Version 1
    plan_res = client.get(f"/events/{event_id}/plan", headers=headers)
    assert plan_res.status_code == status.HTTP_200_OK
    plan_data = plan_res.json()
    assert plan_data["version"] == 1
    assert plan_data["event_id"] == event_id
    plan_json = plan_data["plan"]
    assert plan_json["title"] == "Grand Coastal Reception"
    assert Decimal(str(plan_json["total_budget"])) == Decimal("1200000.00")
    assert len(plan_json["budget"]["categories"]) > 0
    assert len(plan_json["timeline"]) > 0
    assert len(plan_json["checklist"]) > 0
    assert len(plan_json["run_of_show"]) > 0

    # 3. Generate New Plan Version
    regen_res = client.post(f"/events/{event_id}/plan/generate", headers=headers)
    assert regen_res.status_code == status.HTTP_200_OK
    v2_data = regen_res.json()
    assert v2_data["version"] == 2
    assert v2_data["event_id"] == event_id
