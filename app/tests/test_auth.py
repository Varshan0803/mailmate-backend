# app/tests/test_auth.py
import pytest
from httpx import AsyncClient
from app.main import app
import asyncio

@pytest.mark.anyio
async def test_register_and_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # register
        r = await ac.post("/auth/register", json={"name":"t1","email":"t1@example.com","password":"Test1234"})
        assert r.status_code in (200,201)
        # login
        r2 = await ac.post("/auth/login", json={"name":"t1","email":"t1@example.com","password":"Test1234"})
        assert r2.status_code == 200
        token = r2.json().get("access_token")
        assert token
        # get me
        headers = {"Authorization": f"Bearer {token}"}
        r3 = await ac.get("/auth/me", headers=headers)
        assert r3.status_code == 200
