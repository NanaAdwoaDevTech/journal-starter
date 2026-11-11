"""Tests for the /version endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_version_returns_build_commit(client, monkeypatch):
    sha = "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setenv("GIT_SHA", sha)

    response = await client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"commit": sha}


async def test_version_defaults_to_unknown(client, monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)

    response = await client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"commit": "unknown"}
