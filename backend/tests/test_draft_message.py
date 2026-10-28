"""Unit tests for the vendor message drafting engine and endpoint."""

from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.domain.message_drafter import draft_vendor_inquiry
from app.domain.schemas import PlanSchema


def _get_auth_headers(client: TestClient, email: str = "msg_user@example.com") -> dict[str, str]:
    """Helper to register and login a test user, returning auth headers."""
    client.post(
        "/auth/register",
        json={"name": "Message Test User", "email": email, "password": "password1234"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "password1234"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_draft_message_unauthenticated_fails(client: TestClient) -> None:
    """Unauthenticated request must return 401 Unauthorized."""
    headers = _get_auth_headers(client, "owner_msg@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Private Party", "event_type": "birthday", "total_budget": 50000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    res = client.post(
        f"/events/{event_id}/messages/draft",
        json={"vendor_category": "Catering"},
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_draft_message_other_user_event_returns_404(client: TestClient) -> None:
    """Non-owner user cannot draft messages for another user's event."""
    owner_headers = _get_auth_headers(client, "real_event_owner@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Private Wedding", "event_type": "wedding", "total_budget": 300000.0},
        headers=owner_headers,
    )
    event_id = create_res.json()["id"]

    other_headers = _get_auth_headers(client, "intruder_user@example.com")
    res = client.post(
        f"/events/{event_id}/messages/draft",
        json={"vendor_category": "Decor"},
        headers=other_headers,
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_draft_caterer_message_structure_and_grounding(client: TestClient) -> None:
    """Test drafting a caterer message validates Pydantic schema and asks for quotes."""
    headers = _get_auth_headers(client, "birthday_host@example.com")
    create_res = client.post(
        "/events/",
        json={
            "title": "21st Birthday Party",
            "event_type": "birthday",
            "city": "Mangaluru",
            "event_date": "2026-11-20",
            "guest_count": 80,
            "total_budget": 75000.0,
        },
        headers=headers,
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    event_id = create_res.json()["id"]

    res = client.post(
        f"/events/{event_id}/messages/draft",
        json={
            "vendor_category": "Catering",
            "custom_notes": "Vegetarian snacks package with live counters and tea/beverages",
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    draft_data = res.json()

    assert draft_data["vendor_category"] == "Catering"
    assert "Catering" in draft_data["subject"]
    assert "80" in draft_data["event_summary"]
    assert "Mangaluru" in draft_data["event_summary"]
    assert len(draft_data["specific_questions"]) >= 1

    # Invariants: Must ask for quotation and availability, never invent fixed prices
    full_msg = draft_data["full_message"]
    assert "quote" in full_msg.lower() or "quotation" in full_msg.lower()
    assert "availability" in full_msg.lower()
    assert "80" in full_msg


def test_draft_message_with_shortlisted_vendor_name(client: TestClient) -> None:
    """Test providing a specific known vendor name addresses the vendor respectfully."""
    headers = _get_auth_headers(client, "known_vendor_host@example.com")
    create_res = client.post(
        "/events/",
        json={
            "title": "Mangaluru Coastal Celebration",
            "event_type": "birthday",
            "total_budget": 50000.0,
        },
        headers=headers,
    )
    event_id = create_res.json()["id"]

    res = client.post(
        f"/events/{event_id}/messages/draft",
        json={
            "vendor_category": "Catering",
            "vendor_name": "Kudla Rasoi Coastal Caterers",
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    draft_data = res.json()
    assert "Kudla Rasoi" in draft_data["greeting"]
    assert "Kudla Rasoi" in draft_data["full_message"]


def test_draft_message_deterministic_fallback_on_llm_failure(client: TestClient) -> None:
    """Test deterministic fallback triggers seamlessly when LLM raises exception."""
    headers = _get_auth_headers(client, "fallback_test@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Beachside Meet", "event_type": "community", "total_budget": 40000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # Load event & plan
    ev_plan_res = client.get(f"/events/{event_id}/plan", headers=headers)
    plan = PlanSchema.model_validate(ev_plan_res.json()["plan"])

    mock_llm = MagicMock()
    mock_llm.generate_structured.side_effect = RuntimeError("Groq rate limit exceeded")

    ev_record = MagicMock()
    ev_record.title = "Beachside Meet"
    ev_record.event_type = "community"
    ev_record.city = "Mangaluru"
    ev_record.event_date = None
    ev_record.guest_count = 50

    fallback_draft = draft_vendor_inquiry(
        event=ev_record,
        plan=plan,
        vendor_category="Photography",
        client=mock_llm,
    )
    assert fallback_draft.is_template_fallback is True
    assert fallback_draft.vendor_category == "Photography"
    assert "Photography" in fallback_draft.subject
    assert len(fallback_draft.specific_questions) >= 1
    assert "quotation" in fallback_draft.full_message.lower()
