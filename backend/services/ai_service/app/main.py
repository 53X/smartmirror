"""AI service FastAPI application."""

from __future__ import annotations

import json
import threading
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from smartmirror_shared.logging_config import configure_service_logging
from smartmirror_shared.part_types import is_known_part_type
from smartmirror_shared.schemas import JobRecord

from app.jobs import jobs, run_reconstruct_job, run_tryon_job
from app.settings import settings
from app.tryon.factory import get_tryon_vendor

logger = configure_service_logging("ai_service", settings.log_level)

app = FastAPI(title="Smartmirror AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _spawn(target, *args) -> None:
    """Run OpenAI/FASHN off the event loop so job polls are not blocked."""
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe including which Stage B vendor is active."""
    return {"status": "ok", "service": "ai_service", "tryon_vendor": get_tryon_vendor().name}


@app.post("/jobs/reconstruct", response_model=JobRecord)
async def create_reconstruct_job(
    sku_id: UUID = Form(...),
    part_types_json: str = Form(...),
    files: list[UploadFile] = File(...),
) -> JobRecord:
    """Queue Stage A reconstruct from multipart part images."""
    try:
        part_types = json.loads(part_types_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="part_types_json must be a JSON array") from exc
    if not isinstance(part_types, list) or len(part_types) != len(files):
        raise HTTPException(status_code=400, detail="part_types and files length mismatch")
    part_bytes: dict[str, bytes] = {}
    for part_type, upload in zip(part_types, files, strict=True):
        if not is_known_part_type(part_type):
            raise HTTPException(status_code=400, detail=f"Unknown part type: {part_type}")
        payload = await upload.read()
        if not payload:
            raise HTTPException(status_code=400, detail=f"Empty upload for {part_type}")
        part_bytes[part_type] = payload
    record = jobs.create_job("reconstruct", sku_id, vendor="compose_blend")
    _spawn(run_reconstruct_job, record.id, part_bytes)
    return record


@app.post("/jobs/try-on", response_model=JobRecord)
async def create_tryon_job(
    sku_id: UUID = Form(...),
    session_id: str = Form(...),
    reconstructed_asset_url: str = Form(...),
    customer_still: UploadFile = File(...),
) -> JobRecord:
    """Queue Stage B try-on. Customer still is held in memory for the job only."""
    if len(session_id) < 8:
        raise HTTPException(status_code=400, detail="session_id too short")
    still_bytes = await customer_still.read()
    if not still_bytes:
        raise HTTPException(status_code=400, detail="Empty customer still")
    vendor = get_tryon_vendor()
    record = jobs.create_job("try_on", sku_id, vendor=vendor.name)
    _spawn(
        run_tryon_job,
        record.id,
        sku_id,
        session_id,
        reconstructed_asset_url,
        still_bytes,
    )
    return record


@app.get("/jobs/{job_id}", response_model=JobRecord)
def get_job(job_id: UUID) -> JobRecord:
    """Poll reconstruct or try-on job status."""
    return jobs.get_job(job_id)


@app.get("/results/{filename}")
def get_result(filename: str) -> FileResponse:
    """Serve a generated PNG. Gateway should not log this binary."""
    return FileResponse(jobs.result_path(filename))
