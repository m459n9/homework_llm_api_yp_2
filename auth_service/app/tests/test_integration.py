import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_and_me(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"email": "surname@email.com", "password": "strongpass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    resp = await client.post(
        "/auth/login",
        data={"username": "surname@email.com", "password": "strongpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    user = resp.json()
    assert user["email"] == "surname@email.com"
    assert user["role"] == "user"
    assert "id" in user
    assert "created_at" in user


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "dup@email.com", "password": "pass123"},
    )
    resp = await client.post(
        "/auth/register",
        json={"email": "dup@email.com", "password": "pass456"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "user@email.com", "password": "correct"},
    )
    resp = await client.post(
        "/auth/login",
        data={"username": "user@email.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert resp.status_code == 401
