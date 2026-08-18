"""Seed real sari photos so the kiosk is not colored rectangles."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from smartmirror_shared.schemas import SkuCreateRequest

from app.store import CatalogStore

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

DEMO_SARIS = (
    {
        "barcode": "DEMO-001",
        "name": "Bandhani Banarasi work (Wikimedia)",
        "fabric": "silk",
        "file": "demo-001.jpg",
        "attribution": "Kutch.artesania / Wikimedia Commons / CC BY-SA 4.0",
    },
    {
        "barcode": "DEMO-002",
        "name": "Odisha Nivi drape, museum mannequin (Wikimedia)",
        "fabric": "silk",
        "file": "demo-002.jpg",
        "attribution": "Subhashish Panigrahi / Wikimedia Commons / CC BY-SA 3.0",
    },
    {
        "barcode": "DEMO-003",
        "name": "White field, pink vine, pink-yellow zigzag border",
        "fabric": "cotton",
        "file": "demo-003.jpg",
        "attribution": "Store photo (founder capture)",
    },
)


def seed_demo_skus(store: CatalogStore) -> None:
    """Create missing demo SKUs from fixture photographs."""
    existing = {sku.barcode for sku in store.list_skus()}
    for spec in DEMO_SARIS:
        if spec["barcode"] in existing:
            continue
        _add_demo_sku(store, spec)


def _add_demo_sku(store: CatalogStore, spec: dict[str, str]) -> None:
    """Insert one approved demo SKU from a hanging or spread fixture photo."""
    garment = (_FIXTURES / spec["file"]).read_bytes()
    Image.open(BytesIO(garment)).verify()
    sku = store.create_sku(
        SkuCreateRequest(
            barcode=spec["barcode"],
            name=spec["name"],
            fabric=spec["fabric"],
            length_yards=6.0,
            drape_style="nivi",
            stock_count=3,
        )
    )
    store.add_part_bytes(sku.id, "full_hanging", garment, "image/jpeg")
    store.add_part_bytes(sku.id, "pallu", _crop_fraction(garment, 0.0, 0.0, 1.0, 0.32), "image/jpeg")
    store.add_part_bytes(sku.id, "body_field", _crop_fraction(garment, 0.12, 0.28, 0.88, 0.78), "image/jpeg")
    store.add_part_bytes(sku.id, "border", _crop_fraction(garment, 0.0, 0.78, 1.0, 1.0), "image/jpeg")
    store.add_part_bytes(sku.id, "blouse", _crop_fraction(garment, 0.3, 0.32, 0.7, 0.55), "image/jpeg")
    reconstructed = BytesIO()
    Image.open(BytesIO(garment)).convert("RGB").save(reconstructed, format="PNG")
    store.set_reconstructed_asset(sku.id, reconstructed.getvalue())
    store.set_approved(sku.id, True)


def _crop_fraction(jpeg_bytes: bytes, left: float, top: float, right: float, bottom: float) -> bytes:
    """Crop identity regions from the fixture photo for the staff SOP demo."""
    image = Image.open(BytesIO(jpeg_bytes)).convert("RGB")
    box = (
        int(image.width * left),
        int(image.height * top),
        int(image.width * right),
        int(image.height * bottom),
    )
    cropped = image.crop(box)
    buffer = BytesIO()
    cropped.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()
