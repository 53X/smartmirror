"""SKU and media HTTP routes."""

from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from smartmirror_shared.schemas import SkuCreateRequest, SkuRecord

from app.store import store

router = APIRouter()


@router.post("/skus", response_model=SkuRecord)
def create_sku(payload: SkuCreateRequest) -> SkuRecord:
    """Register a sari SKU before staff capture."""
    return store.create_sku(payload)


@router.get("/skus", response_model=list[SkuRecord])
def list_skus(approved_only: bool = Query(default=False)) -> list[SkuRecord]:
    """List catalog SKUs. Kiosk callers should pass approved_only=true."""
    return store.list_skus(approved_only=approved_only)


@router.get("/skus/{sku_id}", response_model=SkuRecord)
def get_sku(sku_id: UUID) -> SkuRecord:
    """Fetch one SKU including parts and reconstruct URL."""
    return store.get_sku(sku_id)


@router.post("/skus/{sku_id}/parts", response_model=SkuRecord)
async def upload_part(
    sku_id: UUID,
    part_type: str = Form(...),
    file: UploadFile = File(...),
) -> SkuRecord:
    """Attach a SOP part photograph to the SKU."""
    return await store.add_part(sku_id, part_type, file)


@router.post("/skus/{sku_id}/reconstructed", response_model=SkuRecord)
async def upload_reconstructed(
    sku_id: UUID,
    file: UploadFile = File(...),
) -> SkuRecord:
    """Store Stage A output and reset the approve flag."""
    image_bytes = await file.read()
    return store.set_reconstructed_asset(sku_id, image_bytes)


@router.post("/skus/{sku_id}/approve", response_model=SkuRecord)
def approve_sku(sku_id: UUID, approved: bool = Query(default=True)) -> SkuRecord:
    """Human approve-before-kiosk gate for pallu and border identity."""
    return store.set_approved(sku_id, approved)


@router.get("/media/{sku_id}/{filename}")
def get_media(sku_id: UUID, filename: str) -> FileResponse:
    """Serve stored part or reconstructed images."""
    path = store.media_path(sku_id, filename)
    return FileResponse(path)
