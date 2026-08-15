"""API tests for Stage A reconstruct and Stage B try-on job create."""

from io import BytesIO
from pathlib import Path
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from smartmirror_shared.part_types import REQUIRED_PART_TYPES

from app.jobs import JobStore
from app.main import app
from app.settings import settings
import app.jobs as jobs_module
import app.main as main_module


def _png(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _wait_job(client: TestClient, job_id: str):
    """Poll until a background thread finishes the job."""
    last = None
    for _ in range(80):
        last = client.get(f"/jobs/{job_id}")
        if last.json()["status"] in {"succeeded", "failed"}:
            return last
        time.sleep(0.05)
    return last


def _client(tmp_path: Path) -> TestClient:
    store = JobStore(tmp_path)
    jobs_module.jobs = store
    main_module.jobs = store
    settings.ai_data_dir = tmp_path
    return TestClient(app)


def test_reconstruct_job_create_and_complete(tmp_path: Path) -> None:
    client = _client(tmp_path)
    sku_id = uuid4()
    data = {
        "sku_id": str(sku_id),
        "part_types_json": json.dumps(list(REQUIRED_PART_TYPES)),
    }
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    colors = [
        (160, 30, 40),
        (40, 80, 140),
        (200, 160, 40),
        (180, 140, 30),
        (90, 20, 90),
    ]
    for part_type, color in zip(REQUIRED_PART_TYPES, colors, strict=True):
        files.append(("files", (f"{part_type}.png", _png(color), "image/png")))

    created = client.post("/jobs/reconstruct", data=data, files=files)
    assert created.status_code == 200
    job_id = created.json()["id"]
    assert created.json()["kind"] == "reconstruct"
    assert created.json()["status"] in {"queued", "succeeded"}

    polled = _wait_job(client, job_id)
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["result_url"].endswith(".png")


def test_tryon_job_create_with_stub(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "tryon_allow_stub", True)
    monkeypatch.setattr(settings, "fal_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    client = _client(tmp_path)
    sari_png = _png((120, 20, 60))
    still_png = _png((210, 180, 160))

    def fake_fetch(_url: str) -> bytes:
        return sari_png

    monkeypatch.setattr(jobs_module, "_fetch_bytes", fake_fetch)

    created = client.post(
        "/jobs/try-on",
        data={
            "sku_id": str(uuid4()),
            "session_id": "kiosk-session-test",
            "reconstructed_asset_url": "http://catalog.local/media/demo/reconstructed.png",
        },
        files={"customer_still": ("still.png", still_png, "image/png")},
    )
    assert created.status_code == 200
    assert created.json()["kind"] == "try_on"
    job_id = created.json()["id"]
    polled = _wait_job(client, job_id)
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["vendor"] == "stub"
