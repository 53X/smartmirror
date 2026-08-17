"""OpenAI try-on retry must keep a mask; prompt must freeze pose."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PIL import Image

from app.tryon.interface import TryOnRequest
from app.tryon.openai_tryon import DRAPE_PROMPT, OpenAITryOnVendor


def _tiny_png(color: tuple[int, int, int] = (180, 140, 120)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 96), color).save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def test_drape_prompt_freezes_pose_and_camera() -> None:
    lowered = DRAPE_PROMPT.lower()
    assert "freeze" in lowered
    assert "pose" in lowered
    assert "limbs" in lowered
    assert "camera" in lowered


def test_mask_rejected_retry_still_sends_mask(monkeypatch) -> None:
    """A 400 on the masked edit retries with a rebuilt mask, never an unmasked 2-file call."""
    posts: list[dict[str, Any]] = []
    success_png = _tiny_png((90, 20, 70))
    b64 = base64.b64encode(success_png).decode("ascii")

    class _FakeClient:
        def __init__(self, timeout: object = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, headers: dict | None = None, data: dict | None = None, files: list | None = None):
            posts.append({"url": url, "data": data, "files": files})
            if len(posts) == 1:
                return _FakeResponse(400, text="invalid mask")
            return _FakeResponse(200, payload={"data": [{"b64_json": b64}]})

    monkeypatch.setattr("app.tryon.openai_tryon.httpx.Client", _FakeClient)
    monkeypatch.setattr("app.tryon.openai_tryon.settings.openai_api_key", "sk-test-not-a-secret")

    vendor = OpenAITryOnVendor()
    result = vendor.generate(
        TryOnRequest(
            customer_still=_tiny_png(),
            reconstructed_sari=_tiny_png((40, 80, 20)),
            sku_id="sku",
            session_id="sess",
            face_box=(18, 8, 28, 32),
        )
    )
    assert result.vendor_name == "openai_gpt_image"
    assert len(posts) == 2
    for call in posts:
        names = [item[0] for item in call["files"]]
        assert "mask" in names
        assert names.count("image[]") == 2
        assert call["data"]["input_fidelity"] == "high"
    assert "pose" in DRAPE_PROMPT.lower()
