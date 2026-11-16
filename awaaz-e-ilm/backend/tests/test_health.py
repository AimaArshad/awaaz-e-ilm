"""Tests for the /health endpoint.

Verifies that the health check returns HTTP 200 and the expected JSON body.
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client):
    """GET /health should return 200 with status=ok."""
    response = await async_client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_body(async_client):
    """GET /health should return {"status": "ok", "version": "0.1.0"}."""
    response = await async_client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_no_auth_required(async_client):
    """Health endpoint must be accessible without authentication."""
    response = await async_client.get("/health")
    assert response.status_code != 401
    assert response.status_code != 403
