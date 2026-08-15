"""Pydantic models shared across gateway, catalog, and AI services."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


JobKind = Literal["reconstruct", "try_on"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]
DrapeStyle = Literal["nivi"]


class SkuCreateRequest(BaseModel):
    """Staff payload to register a sari SKU before part shots."""

    barcode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    fabric: str | None = Field(default=None, max_length=120)
    length_yards: float | None = Field(default=None, ge=4, le=12)
    pallu_shoulder: str = Field(default="left", max_length=32)
    drape_style: DrapeStyle = "nivi"
    price_minor: int | None = Field(default=None, ge=0)
    stock_count: int = Field(default=0, ge=0)
    keep_customer_blouse: bool = False


class PartImage(BaseModel):
    """One stored part photograph for a SKU."""

    part_type: str
    media_url: str
    content_type: str = "image/jpeg"


class SkuRecord(BaseModel):
    """Catalog SKU including reconstruct and approve state."""

    id: UUID
    barcode: str
    name: str
    fabric: str | None
    length_yards: float | None
    pallu_shoulder: str
    drape_style: DrapeStyle
    price_minor: int | None
    stock_count: int
    keep_customer_blouse: bool
    parts: list[PartImage] = Field(default_factory=list)
    reconstructed_asset_url: str | None = None
    approved_for_kiosk: bool = False
    created_at: datetime
    updated_at: datetime


class ReconstructJobRequest(BaseModel):
    """Stage A job: compose part images into a canonical sari asset."""

    sku_id: UUID
    part_images: list[PartImage] = Field(min_length=1)


class TryOnJobRequest(BaseModel):
    """Stage B job: try reconstructed sari onto a customer still."""

    sku_id: UUID
    session_id: str = Field(min_length=8, max_length=80)
    reconstructed_asset_url: str
    customer_still_data_url: str | None = None
    customer_still_url: HttpUrl | None = None


class JobRecord(BaseModel):
    """Async AI job status. Result URLs only — never embed face pixels in logs."""

    id: UUID
    kind: JobKind
    status: JobStatus
    sku_id: UUID | None = None
    result_url: str | None = None
    error_message: str | None = None
    vendor: str = "stub"
    created_at: datetime
    updated_at: datetime
