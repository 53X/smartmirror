"""Gateway auth tests for kiosk vs staff routes."""

from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings


def test_kiosk_rejected_without_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "kiosk_device_token", "secret-kiosk")
    client = TestClient(app)
    response = client.get("/kiosk/skus")
    assert response.status_code == 401


def test_staff_dev_bypass(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_bypass", True)
    client = TestClient(app)
    denied = client.get("/staff/skus")
    assert denied.status_code == 401
    # Downstream catalog is not running; bypass should get past auth (502/500) not 401.
    allowed = client.get("/staff/skus", headers={"Authorization": "Bearer staff-dev"})
    assert allowed.status_code != 401
