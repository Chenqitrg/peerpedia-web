"""Health check endpoint tests."""

import pytest


@pytest.fixture
def client(db_engine):
    from peerpedia_api import deps
    from peerpedia_api.main import app
    from peerpedia_core.storage.db.engine import get_session

    def override_db():
        session = get_session(db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_db
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestHealth:
    def test_health_returns_ok(self, client):
        """GET /health returns 200 with {"ok": true}."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"ok": True}

    def test_health_no_db_query(self, client):
        """Health check should work even without DB dependency."""
        # The endpoint doesn't use get_db, so it works without override
        from fastapi.testclient import TestClient
        from peerpedia_api.main import app

        with TestClient(app) as raw_client:
            resp = raw_client.get("/health")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    def test_health_response_is_fast(self, client):
        """Health check should respond quickly (no heavy ops)."""
        import time

        start = time.time()
        resp = client.get("/health")
        elapsed = time.time() - start

        assert resp.status_code == 200
        # Should complete in well under 1 second (no DB, no computation)
        assert elapsed < 0.5, f"Health check took {elapsed:.3f}s, expected <0.5s"
