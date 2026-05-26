"""GET /api/health — liveness probe."""
import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
