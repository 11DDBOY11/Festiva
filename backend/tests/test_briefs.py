"""Tests for stateless brief parsing logic and API endpoint."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.ai.brief_parser import parse_brief
from app.ai.llm_client import FakeLLMClient
from app.domain.schemas import EventBrief
from app.main import app


def test_parse_brief_deterministic_fallback() -> None:
    raw = (
        "Planning a coastal wedding in Kadri, Mangaluru for around 250 guests with a budget "
        "of 15 lakhs. We need Mangalorean catering and coastal floral decor."
    )
    result = parse_brief(raw_text=raw, client=FakeLLMClient())
    brief = result.brief

    assert brief.event_type == "wedding"
    assert brief.guest_count == 250
    assert brief.total_budget == Decimal("1500000")
    assert brief.city == "Mangaluru"
    # Even if date is missing, date question is asked
    assert "event_date" in brief.missing_fields
    assert any("date" in q.lower() for q in result.clarifying_questions)


def test_parse_brief_with_structured_mock_llm() -> None:
    expected_brief = EventBrief(
        title="Ayaan's 1st Birthday Carnival",
        event_type="birthday",
        event_date=None,
        city="Mangaluru",
        guest_count=75,
        total_budget=Decimal("80000"),
        theme="Jungle Safari",
        dietary_preferences=["Vegetarian buffet", "Cupcake counter"],
        priorities=["Balloon decor", "Kids magic show"],
        missing_fields=["event_date"],
        clarifying_questions=["What specific date are you planning for Ayaan's birthday?"],
    )
    fake_llm = FakeLLMClient(structured_responses={EventBrief: expected_brief})

    result = parse_brief("1st birthday in Mangalore for 75 pax", client=fake_llm)
    assert result.brief.title == "Ayaan's 1st Birthday Carnival"
    assert result.brief.event_type == "birthday"
    assert result.brief.guest_count == 75
    assert result.brief.total_budget == Decimal("80000")
    assert result.needs_clarification is True
    assert len(result.clarifying_questions) >= 1


def test_parse_brief_api_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/briefs/parse",
        json={
            "raw_text": (
                "Need a grand community sports festival in Mangaluru for 500 members, "
                "budget around 3 lakhs."
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "brief" in data
    assert "clarifying_questions" in data
    assert data["brief"]["event_type"] == "community"
    assert data["brief"]["guest_count"] == 500
    assert float(data["brief"]["total_budget"]) == 300000.0


def test_parse_brief_empty_text_fails() -> None:
    client = TestClient(app)
    response = client.post("/briefs/parse", json={"raw_text": "  "})
    assert response.status_code == 422
