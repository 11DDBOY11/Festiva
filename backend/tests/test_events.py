"""Tests for events CRUD endpoints (/events)."""

from fastapi import status
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, email: str = "event_user@example.com") -> dict[str, str]:
    """Helper to register/login a user and return the Authorization header."""
    client.post(
        "/auth/register",
        json={"name": "Event Tester", "email": email, "password": "password1234"},
    )
    res = client.post(
        "/auth/login",
        json={"email": email, "password": "password1234"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_event(client: TestClient) -> None:
    headers = _get_auth_headers(client, "creator@example.com")

    payload = {
        "title": "21st Birthday Bash",
        "event_type": "birthday",
        "event_date": "2026-12-15",
        "city": "Mangaluru",
        "guest_count": 80,
        "total_budget": 75000.0,
        "currency": "INR",
    }
    create_res = client.post("/events/", json=payload, headers=headers)
    assert create_res.status_code == status.HTTP_201_CREATED
    event_data = create_res.json()
    assert event_data["title"] == "21st Birthday Bash"
    assert event_data["city"] == "Mangaluru"
    assert event_data["status"] == "draft"
    event_id = event_data["id"]

    get_res = client.get(f"/events/{event_id}", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == event_id


def test_list_events(client: TestClient) -> None:
    headers = _get_auth_headers(client, "lister@example.com")

    client.post(
        "/events/",
        json={"title": "Event 1", "event_type": "birthday", "city": "Mangaluru"},
        headers=headers,
    )
    client.post(
        "/events/",
        json={"title": "Event 2", "event_type": "wedding", "city": "Mangaluru"},
        headers=headers,
    )

    list_res = client.get("/events/", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    events = list_res.json()
    assert len(events) == 2
    # Newest first
    assert events[0]["title"] == "Event 2"
    assert events[1]["title"] == "Event 1"


def test_patch_event(client: TestClient) -> None:
    headers = _get_auth_headers(client, "patcher@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "Original Title", "event_type": "community", "guest_count": 50},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/events/{event_id}",
        json={"title": "Updated Title", "guest_count": 120},
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    updated = patch_res.json()
    assert updated["title"] == "Updated Title"
    assert updated["guest_count"] == 120
    assert updated["event_type"] == "community"


def test_delete_event(client: TestClient) -> None:
    headers = _get_auth_headers(client, "deleter@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "To Delete", "event_type": "birthday"},
        headers=headers,
    )
    event_id = create_res.json()["id"]

    del_res = client.delete(f"/events/{event_id}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/events/{event_id}", headers=headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_user_cannot_access_other_users_event(client: TestClient) -> None:
    headers_a = _get_auth_headers(client, "user_a@example.com")
    headers_b = _get_auth_headers(client, "user_b@example.com")

    create_res = client.post(
        "/events/",
        json={"title": "User A Private Event", "event_type": "wedding"},
        headers=headers_a,
    )
    event_id = create_res.json()["id"]

    # User B attempts to access User A's event
    get_res = client.get(f"/events/{event_id}", headers=headers_b)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts to delete User A's event
    del_res = client.delete(f"/events/{event_id}", headers=headers_b)
    assert del_res.status_code == status.HTTP_404_NOT_FOUND
