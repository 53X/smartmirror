"""OpenAI try-on retry must keep a mask; edit prompt comes from compose_tryon_prompt."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PIL import Image

from app.tryon.garment_prompt import compose_tryon_prompt
from app.tryon.interface import TryOnRequest
from app.tryon.openai_tryon import OpenAITryOnVendor


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


def test_compose_prompt_for_shirt_does_not_require_sari() -> None:
    prompt = compose_tryon_prompt(
        clothing_description="a red plaid flannel shirt",
        garment_category="tops",
    )
    lowered = prompt.lower()
    assert "a red plaid flannel shirt" in prompt
    assert "freeze" in lowered
    assert "pose" in lowered
    assert "sari" not in lowered


def test_mask_rejected_retry_still_sends_mask(monkeypatch) -> None:
    """A 400 on the masked edit retries with a rebuilt mask, never an unmasked 2-file call."""
    posts: list[dict[str, Any]] = []
    success_png = _tiny_png((90, 20, 70))
    b64 = base64.b64encode(success_png).decode("ascii")
    expected_prompt = compose_tryon_prompt(
        clothing_description="a red plaid flannel shirt",
        garment_category="tops",
    )

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
            clothing_description="a red plaid flannel shirt",
            garment_category="tops",
        )
    )
    assert result.vendor_name == "openai_gpt_image"
    assert len(posts) == 2
    for call in posts:
        names = [item[0] for item in call["files"]]
        filenames = [item[1][0] for item in call["files"] if item[0] == "image[]"]
        assert "mask" in names
        assert names.count("image[]") == 2
        assert "garment.png" in filenames
        assert "sari.png" not in filenames
        assert call["data"]["input_fidelity"] == "high"
        assert call["data"]["prompt"] == expected_prompt
        assert "sari" not in call["data"]["prompt"].lower()
