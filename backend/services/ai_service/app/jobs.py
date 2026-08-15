"""AI job orchestration for reconstruct and try-on."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from smartmirror_shared.logging_config import configure_service_logging, safe_event
from smartmirror_shared.schemas import JobRecord

from app.reconstruct import reconstruct_from_part_bytes
from app.settings import settings
from app.tryon.factory import get_tryon_vendor
from app.tryon.interface import TryOnRequest

logger = configure_service_logging("ai_service", settings.log_level)


class JobStore:
    """In-memory jobs with PNG results on disk. Does not persist face pixels in logs."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._results_dir = data_dir / "results"
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[UUID, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, kind: str, sku_id: UUID | None, vendor: str) -> JobRecord:
        """Register a queued job and return it."""
        now = datetime.now(UTC)
        record = JobRecord(
            id=uuid4(),
            kind=kind,  # type: ignore[arg-type]
            status="queued",
            sku_id=sku_id,
            vendor=vendor,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[record.id] = record
        logger.info("job_created %s", safe_event({"job_id": str(record.id), "kind": kind}))
        return record

    def get_job(self, job_id: UUID) -> JobRecord:
        """Return a job or 404."""
        with self._lock:
            record = self._jobs.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return record

    def complete(self, job_id: UUID, image_png: bytes) -> JobRecord:
        """Write result PNG and mark the job succeeded."""
        path = self._results_dir / f"{job_id}.png"
        path.write_bytes(image_png)
        url = f"/results/{job_id}.png"
        with self._lock:
            record = self._jobs[job_id]
            updated = record.model_copy(
                update={
                    "status": "succeeded",
                    "result_url": url,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._jobs[job_id] = updated
            return updated

    def fail(self, job_id: UUID, message: str) -> JobRecord:
        """Mark the job failed without storing images."""
        with self._lock:
            record = self._jobs[job_id]
            updated = record.model_copy(
                update={
                    "status": "failed",
                    "error_message": message,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._jobs[job_id] = updated
            return updated

    def result_path(self, filename: str) -> Path:
        """Resolve a result PNG, blocking path traversal."""
        if "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = (self._results_dir / filename).resolve()
        if not str(path).startswith(str(self._results_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Result not found")
        return path


jobs = JobStore(settings.ai_data_dir)


def run_reconstruct_job(job_id: UUID, part_bytes: dict[str, bytes]) -> None:
    """Compose part shots into a canonical sari PNG."""
    try:
        png = reconstruct_from_part_bytes(part_bytes)
        jobs.complete(job_id, png)
        logger.info("reconstruct_succeeded %s", safe_event({"job_id": str(job_id)}))
    except Exception as exc:  # noqa: BLE001 — job boundary
        jobs.fail(job_id, str(exc))
        logger.exception("reconstruct_failed %s", safe_event({"job_id": str(job_id)}))


def run_tryon_job(
    job_id: UUID,
    sku_id: UUID,
    session_id: str,
    reconstructed_asset_url: str,
    customer_still: bytes,
) -> None:
    """Run Stage B using stub or hosted vendor. Customer still is not logged."""
    try:
        sari_bytes = _fetch_bytes(reconstructed_asset_url)
        vendor = get_tryon_vendor()
        result = vendor.generate(
            TryOnRequest(
                customer_still=customer_still,
                reconstructed_sari=sari_bytes,
                sku_id=str(sku_id),
                session_id=session_id,
            )
        )
        jobs.complete(job_id, result.image_png)
        logger.info(
            "tryon_succeeded %s",
            safe_event({"job_id": str(job_id), "vendor": result.vendor_name, "session_id": session_id}),
        )
    except Exception as exc:  # noqa: BLE001 — job boundary
        jobs.fail(job_id, str(exc))
        logger.exception("tryon_failed %s", safe_event({"job_id": str(job_id), "session_id": session_id}))


def _fetch_bytes(url: str) -> bytes:
    if url.startswith("http://") or url.startswith("https://"):
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    raise ValueError("reconstructed_asset_url must be http(s)")
