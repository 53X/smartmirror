"""API tests for SKU create, parts, reconstruct asset, and approve."""

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from smartmirror_shared.part_types import REQUIRED_PART_TYPES
from smartmirror_shared.schemas import SkuRecord

from app.main import app
from app.settings import settings
from app.store import CatalogStore
import app.routers as routers_module
import app.store as store_module


def _png_bytes(color: tuple[int, int, int] = (180, 40, 70)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _client(tmp_path: Path) -> TestClient:
    catalog = CatalogStore(tmp_path)
    store_module.store = catalog
    routers_module.store = catalog
    settings.catalog_data_dir = tmp_path
    settings.public_media_base_url = "http://testserver"
    settings.catalog_seed_demo = False
    return TestClient(app)


def test_create_sku_and_list(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/skus",
        json={"barcode": "SM-001", "name": "Demo Banarasi"},
    )
    assert created.status_code == 200
    sku_id = created.json()["id"]
    listed = client.get("/skus")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == sku_id
    assert listed.json()[0]["approved_for_kiosk"] is False
    assert listed.json()[0].get("garment_category") in (None, "other")


def test_create_sku_persists_garment_category(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/skus",
        json={"barcode": "SM-TOPS", "name": "Plaid Shirt", "garment_category": "tops"},
    )
    assert created.status_code == 200
    assert created.json()["garment_category"] == "tops"


def test_sku_record_json_without_garment_category_validates() -> None:
    record = SkuRecord.model_validate(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "barcode": "LEGACY",
            "name": "Legacy Nivi",
            "fabric": None,
            "length_yards": 6.0,
            "pallu_shoulder": "left",
            "drape_style": "nivi",
            "price_minor": None,
            "stock_count": 0,
            "keep_customer_blouse": False,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    )
    assert record.garment_category is None


def test_parts_reconstruct_and_approve(tmp_path: Path) -> None:
    client = _client(tmp_path)
    sku_id = client.post(
        "/skus",
        json={"barcode": "SM-002", "name": "Demo Kanjeevaram"},
    ).json()["id"]

    for part_type in REQUIRED_PART_TYPES:
        response = client.post(
            f"/skus/{sku_id}/parts",
            data={"part_type": part_type},
            files={"file": ("part.png", _png_bytes(), "image/png")},
        )
        assert response.status_code == 200

    reject = client.post(f"/skus/{sku_id}/approve?approved=true")
    assert reject.status_code == 400

    reconstructed = client.post(
        f"/skus/{sku_id}/reconstructed",
        files={"file": ("recon.png", _png_bytes((20, 80, 40)), "image/png")},
    )
    assert reconstructed.status_code == 200
    assert reconstructed.json()["reconstructed_asset_url"].endswith("reconstructed.png")
    assert reconstructed.json()["approved_for_kiosk"] is False

    approved = client.post(f"/skus/{sku_id}/approve?approved=true")
    assert approved.status_code == 200
    assert approved.json()["approved_for_kiosk"] is True

    kiosk_list = client.get("/skus?approved_only=true")
    assert len(kiosk_list.json()) == 1
