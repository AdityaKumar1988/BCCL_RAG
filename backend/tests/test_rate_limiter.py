import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.rate_limiter import RateLimiterMiddleware

def test_rate_limiter_middleware_enforcement():
    limiter = RateLimiterMiddleware.get_instance()
    if limiter:
        limiter.reset()

    client = TestClient(app)

    # Health check is exempt
    for _ in range(10):
        res = client.get("/health")
        assert res.status_code == 200

    # Rate limit test on general routes
    hit_429 = False
    for i in range(140):
        res = client.get("/api/documents")
        if res.status_code == 429:
            hit_429 = True
            assert "Rate limit exceeded" in res.json()["detail"]
            assert "X-RateLimit-Limit" in res.headers
            assert "Retry-After" in res.headers
            break
        elif res.status_code == 200:
            assert "X-RateLimit-Remaining" in res.headers

    assert hit_429 is True, "Rate limiter did not return HTTP 429 after exceeding request limit"

    # Reset limiter after test for subsequent test suites
    if limiter:
        limiter.reset()
