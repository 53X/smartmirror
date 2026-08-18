"""Gateway FastAPI application: staff vs kiosk routes."""

from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from smartmirror_shared.logging_config import configure_service_logging

from app.auth import require_kiosk, require_staff
from app.proxy import proxy_json, proxy_multipart, proxy_stream, read_upload
from app.settings import settings

logger = configure_service_logging("gateway", settings.log_level)

app = FastAPI(title="Smartmirror Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Gateway liveness probe."""
    return {"status": "ok", "service": "gateway"}


@app.get("/kiosk/skus")
async def kiosk_skus(_role: str = Depends(require_kiosk)) -> Response:
    """Approved SKUs only for the store kiosk."""
    return await proxy_json("GET", settings.catalog_base_url, "/skus", params={"approved_only": "true"})


@app.get("/kiosk/skus/{sku_id}")
async def kiosk_sku(sku_id: UUID, _role: str = Depends(require_kiosk)) -> Response:
    """One approved SKU. Rejects unapproved items at the BFF."""
    response = await proxy_json("GET", settings.catalog_base_url, f"/skus/{sku_id}")
    return response


@app.post("/kiosk/try-on")
async def kiosk_try_on(
    sku_id: UUID = Form(...),
    session_id: str = Form(...),
    reconstructed_asset_url: str = Form(...),
    customer_still: UploadFile = File(...),
    garment_category: str | None = Form(default=None),
    drape_style: str | None = Form(default=None),
    _role: str = Depends(require_kiosk),
) -> Response:
    """Queue Stage B without logging the customer still."""
    filename, payload, content_type = await read_upload(customer_still)
    data: dict[str, str] = {
        "sku_id": str(sku_id),
        "session_id": session_id,
        "reconstructed_asset_url": reconstructed_asset_url,
    }
    if garment_category:
        data["garment_category"] = garment_category
    if drape_style:
        data["drape_style"] = drape_style
    return await proxy_multipart(
        settings.ai_service_base_url,
        "/jobs/try-on",
        data=data,
        files=[("customer_still", (filename, payload, content_type))],
    )


@app.get("/kiosk/jobs/{job_id}")
async def kiosk_job(job_id: UUID, _role: str = Depends(require_kiosk)) -> Response:
    """Poll a try-on job from the kiosk."""
    return await proxy_json("GET", settings.ai_service_base_url, f"/jobs/{job_id}")


@app.get("/kiosk/media/{sku_id}/{filename}")
async def kiosk_media(sku_id: UUID, filename: str, _role: str = Depends(require_kiosk)):
    """Stream catalog media to the kiosk display."""
    return await proxy_stream(settings.catalog_base_url, f"/media/{sku_id}/{filename}")


@app.get("/kiosk/results/{filename}")
async def kiosk_results(filename: str, _role: str = Depends(require_kiosk)):
    """Stream a generated try-on still."""
    return await proxy_stream(settings.ai_service_base_url, f"/results/{filename}")


@app.get("/staff/part-types")
async def staff_part_types(_role: str = Depends(require_staff)) -> Response:
    """Capture SOP part types for guided staff UI."""
    return await proxy_json("GET", settings.catalog_base_url, "/part-types")


@app.post("/staff/skus")
async def staff_create_sku(request: Request, _role: str = Depends(require_staff)) -> Response:
    """Create a SKU before part capture."""
    body = await request.json()
    return await proxy_json("POST", settings.catalog_base_url, "/skus", json_body=body)


@app.get("/staff/skus")
async def staff_list_skus(_role: str = Depends(require_staff)) -> Response:
    """List all SKUs including drafts."""
    return await proxy_json("GET", settings.catalog_base_url, "/skus")


@app.get("/staff/skus/{sku_id}")
async def staff_get_sku(sku_id: UUID, _role: str = Depends(require_staff)) -> Response:
    """Staff SKU detail including unapproved reconstructs."""
    return await proxy_json("GET", settings.catalog_base_url, f"/skus/{sku_id}")


@app.post("/staff/skus/{sku_id}/parts")
async def staff_upload_part(
    sku_id: UUID,
    part_type: str = Form(...),
    file: UploadFile = File(...),
    _role: str = Depends(require_staff),
) -> Response:
    """Upload one SOP part shot."""
    filename, payload, content_type = await read_upload(file)
    return await proxy_multipart(
        settings.catalog_base_url,
        f"/skus/{sku_id}/parts",
        data={"part_type": part_type},
        files=[("file", (filename, payload, content_type))],
    )


@app.post("/staff/skus/{sku_id}/reconstruct")
async def staff_reconstruct(
    sku_id: UUID,
    _role: str = Depends(require_staff),
) -> Response:
    """Pull stored parts from catalog and queue Stage A on the AI service."""
    sku_response = await proxy_json("GET", settings.catalog_base_url, f"/skus/{sku_id}")
    if sku_response.status_code >= 400:
        return sku_response
    import json

    sku = json.loads(sku_response.body)
    parts = sku.get("parts") or []
    if not parts:
        return Response(content=b'{"detail":"No part images uploaded"}', status_code=400, media_type="application/json")

    files: list[tuple[str, tuple[str, bytes, str]]] = []
    part_types: list[str] = []
    import httpx

    async with httpx.AsyncClient(timeout=60) as client:
        for part in parts:
            media = await client.get(part["media_url"])
            media.raise_for_status()
            part_types.append(part["part_type"])
            files.append(("files", (f"{part['part_type']}.jpg", media.content, part.get("content_type", "image/jpeg"))))

    data: dict[str, str | list[str]] = {
        "sku_id": str(sku_id),
        "part_types_json": json.dumps(part_types),
    }
    return await proxy_multipart(settings.ai_service_base_url, "/jobs/reconstruct", data=data, files=files)


@app.post("/staff/skus/{sku_id}/reconstructed")
async def staff_save_reconstructed(
    sku_id: UUID,
    file: UploadFile = File(...),
    _role: str = Depends(require_staff),
) -> Response:
    """Save Stage A PNG onto the SKU (clears kiosk approval)."""
    filename, payload, content_type = await read_upload(file)
    return await proxy_multipart(
        settings.catalog_base_url,
        f"/skus/{sku_id}/reconstructed",
        data={},
        files=[("file", (filename, payload, content_type))],
    )


@app.post("/staff/skus/{sku_id}/approve")
async def staff_approve(
    sku_id: UUID,
    approved: bool = Query(default=True),
    _role: str = Depends(require_staff),
) -> Response:
    """Human approve-before-kiosk."""
    return await proxy_json(
        "POST",
        settings.catalog_base_url,
        f"/skus/{sku_id}/approve",
        params={"approved": str(approved).lower()},
    )


@app.get("/staff/jobs/{job_id}")
async def staff_job(job_id: UUID, _role: str = Depends(require_staff)) -> Response:
    """Poll Stage A or Stage B jobs from staff UI."""
    return await proxy_json("GET", settings.ai_service_base_url, f"/jobs/{job_id}")


@app.get("/staff/results/{filename}")
async def staff_results(filename: str, _role: str = Depends(require_staff)):
    """Stream AI result PNGs to staff."""
    return await proxy_stream(settings.ai_service_base_url, f"/results/{filename}")


@app.get("/staff/media/{sku_id}/{filename}")
async def staff_media(sku_id: UUID, filename: str, _role: str = Depends(require_staff)):
    """Stream catalog media to staff capture UI."""
    return await proxy_stream(settings.catalog_base_url, f"/media/{sku_id}/{filename}")
