"""Unit tests for the PDF export service and endpoint."""

import io

import pypdf
from fastapi import status
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, email: str = "pdf_user@example.com") -> dict[str, str]:
    """Helper to register and login a test user, returning auth headers."""
    client.post(
        "/auth/register",
        json={"name": "PDF Test User", "email": email, "password": "password1234"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "password1234"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_export_pdf_unauthenticated_fails(client: TestClient) -> None:
    """Unauthenticated request must return 401 Unauthorized."""
    headers = _get_auth_headers(client, "owner_pdf@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Private Gala", "event_type": "birthday", "total_budget": 50000.0},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    res = client.get(f"/events/{event_id}/export.pdf")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_export_pdf_other_user_event_returns_404(client: TestClient) -> None:
    """Non-owner user cannot export another user's event plan."""
    owner_headers = _get_auth_headers(client, "real_owner@example.com")
    create_res = client.post(
        "/events/",
        json={"title": "Secret Event", "event_type": "wedding", "total_budget": 200000.0},
        headers=owner_headers,
    )
    event_id = create_res.json()["id"]

    other_headers = _get_auth_headers(client, "intruder@example.com")
    res = client.get(f"/events/{event_id}/export.pdf", headers=other_headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_export_pdf_success_and_content_verification(client: TestClient) -> None:
    """Authenticated owner exports plan as print-styled PDF; verifies layout and text."""
    headers = _get_auth_headers(client, "mangaluru_pdf@example.com")
    create_res = client.post(
        "/events/",
        json={
            "title": "Coastal Milestone Birthday",
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

    res = client.get(f"/events/{event_id}/export.pdf", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.headers["content-type"] == "application/pdf"
    assert f"festiva_plan_{event_id}_v1.pdf" in res.headers["content-disposition"]

    pdf_bytes = res.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Parse with PyPDF and assert required sections and sample vendor notice
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = " ".join(page.extract_text() for page in reader.pages)
    assert "Coastal Milestone Birthday" in extracted_text
    assert "Mangaluru" in extracted_text
    assert "75,000" in extracted_text
    assert "1. BUDGET BREAKDOWN & ALLOCATIONS" in extracted_text.upper()
    assert "2. PLANNING TIMELINE & ACTION MILESTONES" in extracted_text.upper()
    assert "3. EVENT DAY RUN-OF-SHOW ITINERARY" in extracted_text.upper()
    assert "4. GROUNDED VENDOR SHORTLIST & BOOKING CHECKLIST" in extracted_text.upper()
    # Sample data disclaimer should be present for sample vendors
    assert "Sample Data" in extracted_text or "DEMONSTRATION DATA" in extracted_text


def test_export_specific_plan_version(client: TestClient) -> None:
    """Exporting with ?version= returns the exact requested version in the PDF."""
    headers = _get_auth_headers(client, "versioned_pdf@example.com")
    create_res = client.post(
        "/events/",
        json={
            "title": "Versioned Celebration",
            "event_type": "birthday",
            "city": "Mangaluru",
            "total_budget": 50000.0,
        },
        headers=headers,
    )
    event_id = create_res.json()["id"]

    # Propose and accept a change to create v2
    prop_res = client.post(
        f"/events/{event_id}/changes/propose",
        json={"prompt": "reduce decor by 5000", "base_version": 1},
        headers=headers,
    )
    change_id = prop_res.json()["id"]

    accept_res = client.post(
        f"/events/{event_id}/changes/{change_id}/accept",
        headers=headers,
    )
    assert accept_res.status_code == status.HTTP_200_OK
    assert accept_res.json()["version"] == 2

    # Export v1 explicitly
    v1_res = client.get(f"/events/{event_id}/export.pdf?version=1", headers=headers)
    assert v1_res.status_code == status.HTTP_200_OK
    reader_v1 = pypdf.PdfReader(io.BytesIO(v1_res.content))
    text_v1 = " ".join(page.extract_text() for page in reader_v1.pages)
    assert "Plan Version 1" in text_v1

    # Export v2 explicitly
    v2_res = client.get(f"/events/{event_id}/export.pdf?version=2", headers=headers)
    assert v2_res.status_code == status.HTTP_200_OK
    reader_v2 = pypdf.PdfReader(io.BytesIO(v2_res.content))
    text_v2 = " ".join(page.extract_text() for page in reader_v2.pages)
    assert "Plan Version 2" in text_v2
