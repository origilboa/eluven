"""Integration smoke tests for API boot."""

from main import app


def test_app_exposes_v1_router() -> None:
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    assert any(path.startswith("/api/v1/tasks") for path in paths)
