"""Seed two real Wikimedia sari photos so the kiosk is not colored rectangles."""

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
)


def seed_demo_skus(store: CatalogStore) -> None:
    """Create two approved demo SKUs from fixture photographs when empty."""
    if store.list_skus():
        return
    for spec in DEMO_SARIS:
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
        store.add_part_bytes(sku.id, "pallu", _crop_fraction(garment, 0.0, 0.0, 1.0, 0.35), "image/jpeg")
        store.add_part_bytes(sku.id, "body_field", _crop_fraction(garment, 0.1, 0.25, 0.9, 0.85), "image/jpeg")
        store.add_part_bytes(sku.id, "border", _crop_fraction(garment, 0.0, 0.78, 1.0, 1.0), "image/jpeg")
        store.add_part_bytes(sku.id, "blouse", _crop_fraction(garment, 0.3, 0.28, 0.7, 0.52), "image/jpeg")
        store.set_reconstructed_asset(sku.id, garment)
        store.set_approved(sku.id, True)


def _crop_fraction(jpeg_bytes: bytes, left: float, top: float, right: float, bottom: float) -> bytes:
    """Crop identity regions from the hanging photo for the staff SOP demo."""
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
