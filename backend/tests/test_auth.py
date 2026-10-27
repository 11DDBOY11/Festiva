"""Tests for auth endpoints, token rotation, reuse detection, and prod secret validation."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import Settings


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


def test_token_refresh_rotation(client: TestClient) -> None:
    """Verify refresh token rotation: old token is invalidated, new pair issued."""
    client.post(
        "/auth/register",
        json={
            "name": "Rotation User",
            "email": "rotation@example.com",
            "password": "password1234",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "rotation@example.com", "password": "password1234"},
    )
    rt1 = login_res.json()["refresh_token"]

    # First refresh: rt1 -> rt2
    refresh1_res = client.post("/auth/refresh", json={"refresh_token": rt1})
    assert refresh1_res.status_code == status.HTTP_200_OK
    rt2 = refresh1_res.json()["refresh_token"]
    assert rt2 != rt1

    # Second refresh: rt2 -> rt3
    refresh2_res = client.post("/auth/refresh", json={"refresh_token": rt2})
    assert refresh2_res.status_code == status.HTTP_200_OK
    rt3 = refresh2_res.json()["refresh_token"]
    assert rt3 != rt2


def test_token_reuse_revokes_all_active_tokens(client: TestClient) -> None:
    """Verify token reuse detection: replaying rt1 revokes active rt2 and returns 401."""
    client.post(
        "/auth/register",
        json={
            "name": "Reuse User",
            "email": "reuse@example.com",
            "password": "password1234",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "reuse@example.com", "password": "password1234"},
    )
    rt1 = login_res.json()["refresh_token"]

    # Legitimate refresh: rt1 -> rt2 (rt1 is now revoked)
    refresh1_res = client.post("/auth/refresh", json={"refresh_token": rt1})
    assert refresh1_res.status_code == status.HTTP_200_OK
    rt2 = refresh1_res.json()["refresh_token"]

    # Attacker or replay of rt1: must fail with 401 and trigger cascade revocation
    replay_res = client.post("/auth/refresh", json={"refresh_token": rt1})
    assert replay_res.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token reuse detected" in replay_res.json()["detail"]

    # Now rt2 should ALSO be revoked as a security measure
    subsequent_res = client.post("/auth/refresh", json={"refresh_token": rt2})
    assert subsequent_res.status_code == status.HTTP_401_UNAUTHORIZED


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


def test_startup_fails_in_non_dev_with_default_secret() -> None:
    """Verify Fix 3: settings fails validation if JWT_SECRET is default and ENV != dev."""
    with pytest.raises(ValueError, match="JWT_SECRET cannot be a default value"):
        Settings(
            ENV="production",
            JWT_SECRET="change-me-to-a-random-string",
            SECRET_KEY="change-me-to-a-random-string",
        )

    # Valid non-dev config must succeed
    valid_settings = Settings(
        ENV="production",
        JWT_SECRET="super-secure-production-secret-key-12345678",
    )
    assert valid_settings.ENV == "production"
