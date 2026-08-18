"""JSON + filesystem SKU store. Supabase is wired later when env keys exist."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from smartmirror_shared.part_types import is_known_part_type
from smartmirror_shared.schemas import PartImage, SkuCreateRequest, SkuRecord

from app.settings import settings


class CatalogStore:
    """Thread-safe local catalog used until Supabase Postgres is connected."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._skus_path = data_dir / "skus.json"
        self._media_dir = data_dir / "media"
        self._lock = threading.Lock()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._media_dir.mkdir(parents=True, exist_ok=True)
        if not self._skus_path.exists():
            self._skus_path.write_text("[]", encoding="utf-8")

    def list_skus(self, approved_only: bool = False) -> list[SkuRecord]:
        """Return SKUs, optionally limited to kiosk-approved items."""
        with self._lock:
            records = self._load_unlocked()
        if approved_only:
            return [sku for sku in records if sku.approved_for_kiosk]
        return records

    def get_sku(self, sku_id: UUID) -> SkuRecord:
        """Return one SKU or raise 404."""
        for sku in self.list_skus():
            if sku.id == sku_id:
                return sku
        raise HTTPException(status_code=404, detail="SKU not found")

    def create_sku(self, payload: SkuCreateRequest) -> SkuRecord:
        """Persist a new SKU with empty parts."""
        now = datetime.now(UTC)
        record = SkuRecord(
            id=uuid4(),
            barcode=payload.barcode,
            name=payload.name,
            fabric=payload.fabric,
            length_yards=payload.length_yards,
            pallu_shoulder=payload.pallu_shoulder,
            drape_style=payload.drape_style,
            garment_category=payload.garment_category,
            price_minor=payload.price_minor,
            stock_count=payload.stock_count,
            keep_customer_blouse=payload.keep_customer_blouse,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            records = self._load_unlocked()
            records.append(record)
            self._save_unlocked(records)
        return record

    async def add_part(self, sku_id: UUID, part_type: str, upload: UploadFile) -> SkuRecord:
        """Store a part image on disk and attach it to the SKU."""
        content = await upload.read()
        return self.add_part_bytes(
            sku_id,
            part_type,
            content,
            upload.content_type or "image/jpeg",
        )

    def add_part_bytes(
        self,
        sku_id: UUID,
        part_type: str,
        content: bytes,
        content_type: str = "image/png",
    ) -> SkuRecord:
        """Store raw part-image bytes (used by HTTP upload and local seed)."""
        if not is_known_part_type(part_type):
            raise HTTPException(status_code=400, detail=f"Unknown part type: {part_type}")
        if not content:
            raise HTTPException(status_code=400, detail="Empty image upload")
        suffix = _suffix_for_content_type(content_type)
        sku_dir = self._media_dir / str(sku_id)
        sku_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{part_type}{suffix}"
        (sku_dir / filename).write_bytes(content)
        media_url = f"{settings.public_media_base_url}/media/{sku_id}/{filename}"
        part = PartImage(
            part_type=part_type,
            media_url=media_url,
            content_type=content_type or "image/jpeg",
        )
        with self._lock:
            records = self._load_unlocked()
            sku = _find_sku(records, sku_id)
            sku.parts = [item for item in sku.parts if item.part_type != part_type]
            sku.parts.append(part)
            sku.approved_for_kiosk = False
            sku.updated_at = datetime.now(UTC)
            self._save_unlocked(records)
            return sku

    def set_reconstructed_asset(self, sku_id: UUID, image_bytes: bytes) -> SkuRecord:
        """Save Stage A output and clear kiosk approval until staff re-checks."""
        sku_dir = self._media_dir / str(sku_id)
        sku_dir.mkdir(parents=True, exist_ok=True)
        filename = "reconstructed.png"
        (sku_dir / filename).write_bytes(image_bytes)
        media_url = f"{settings.public_media_base_url}/media/{sku_id}/{filename}"
        with self._lock:
            records = self._load_unlocked()
            sku = _find_sku(records, sku_id)
            sku.reconstructed_asset_url = media_url
            sku.approved_for_kiosk = False
            sku.updated_at = datetime.now(UTC)
            self._save_unlocked(records)
            return sku

    def set_approved(self, sku_id: UUID, approved: bool) -> SkuRecord:
        """Toggle kiosk visibility after a human pallu/border check."""
        with self._lock:
            records = self._load_unlocked()
            sku = _find_sku(records, sku_id)
            if approved and not sku.reconstructed_asset_url:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot approve a SKU without a reconstructed asset",
                )
            sku.approved_for_kiosk = approved
            sku.updated_at = datetime.now(UTC)
            self._save_unlocked(records)
            return sku

    def media_path(self, sku_id: UUID, filename: str) -> Path:
        """Resolve a stored media file, blocking path traversal."""
        if "/" in filename or "\\" in filename or filename.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid media filename")
        path = (self._media_dir / str(sku_id) / filename).resolve()
        if not str(path).startswith(str(self._media_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid media path")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Media not found")
        return path

    def _load_unlocked(self) -> list[SkuRecord]:
        raw = json.loads(self._skus_path.read_text(encoding="utf-8"))
        return [SkuRecord.model_validate(item) for item in raw]

    def _save_unlocked(self, records: list[SkuRecord]) -> None:
        payload = [record.model_dump(mode="json") for record in records]
        self._skus_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _find_sku(records: list[SkuRecord], sku_id: UUID) -> SkuRecord:
    for sku in records:
        if sku.id == sku_id:
            return sku
    raise HTTPException(status_code=404, detail="SKU not found")


def _suffix_for_content_type(content_type: str | None) -> str:
    mapping = {
        "image/png": ".png",
        "image/webp": ".webp",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }
    return mapping.get(content_type or "", ".jpg")


store = CatalogStore(settings.catalog_data_dir)
