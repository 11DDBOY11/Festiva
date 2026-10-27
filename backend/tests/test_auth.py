"""Tests for auth endpoints (/auth/register, /auth/login, /auth/refresh, /auth/me)."""

from fastapi import status
from fastapi.testclient import TestClient


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "Darshan Test",
            "email": "darshan@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Darshan Test"
    assert data["email"] == "darshan@example.com"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client: TestClient) -> None:
    payload = {
        "name": "Darshan Test",
        "email": "darshan_dup@example.com",
        "password": "securepassword123",
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == status.HTTP_201_CREATED

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in res2.json()["detail"]


def test_login_success(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Login User",
            "email": "login@example.com",
            "password": "password1234",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password1234"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Login User",
            "email": "login_wrong@example.com",
            "password": "password1234",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "login_wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_token_refresh(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Refresh User",
            "email": "refresh@example.com",
            "password": "password1234",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "password1234"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == status.HTTP_200_OK
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_me_endpoint(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Me User",
            "email": "me@example.com",
            "password": "password1234",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "password1234"},
    )
    token = login_res.json()["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["email"] == "me@example.com"
    assert data["name"] == "Me User"
