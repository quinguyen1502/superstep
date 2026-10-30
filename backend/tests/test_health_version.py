"""GET /api/health reports the superstep-backend version (TASK-0149, DEC-0068)."""
from importlib.metadata import PackageNotFoundError, version

from fastapi.testclient import TestClient

from app.api.routes.meta import backend_version
from app.main import app


def test_health_reports_the_backend_version():
    data = TestClient(app).get("/api/health").json()["data"]
    assert data["version"] == backend_version()
    assert data["ok"] is True and data["database"] and "run_bus" in data and "import_enabled" in data
    try:
        assert data["version"] == version("superstep-backend")
    except PackageNotFoundError:
        assert data["version"] and data["version"] != "unknown"
