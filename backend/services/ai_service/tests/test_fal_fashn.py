"""FASHN payload uses mapped category; never a drape/compose prompt."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from app.tryon.fal_fashn import FalFashnVendor
from app.tryon.interface import TryOnRequest


def _tiny_png(color: tuple[int, int, int] = (40, 80, 20)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: dict[str, Any] | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


def _install_httpx(monkeypatch, posted: list[dict[str, Any]]) -> None:
    result_png = _tiny_png((90, 20, 70))

    class _FakeClient:
        def __init__(self, timeout: object = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, headers: dict | None = None, json: dict | None = None):
            posted.append({"url": url, "json": json, "headers": headers})
            return _FakeResponse(
                payload={"images": [{"url": "https://fal.example/result.png"}]}
            )

        def get(self, url: str):
            return _FakeResponse(content=result_png)

    monkeypatch.setattr("app.tryon.fal_fashn.httpx.Client", _FakeClient)
    monkeypatch.setattr("app.tryon.fal_fashn.settings.fal_key", "fal-test-key")


def test_fashn_category_tops(monkeypatch) -> None:
    posted: list[dict[str, Any]] = []
    _install_httpx(monkeypatch, posted)
    vendor = FalFashnVendor()
    vendor.generate(
        TryOnRequest(
            customer_still=_tiny_png(),
            reconstructed_sari=_tiny_png((10, 20, 30)),
            sku_id="sku",
            session_id="sess",
            garment_category="tops",
        )
    )
    payload = posted[0]["json"]
    assert payload["category"] == "tops"
    assert "prompt" not in payload


def test_fashn_category_saree_maps_to_one_pieces(monkeypatch) -> None:
    posted: list[dict[str, Any]] = []
    _install_httpx(monkeypatch, posted)
    vendor = FalFashnVendor()
    vendor.generate(
        TryOnRequest(
            customer_still=_tiny_png(),
            reconstructed_sari=_tiny_png((10, 20, 30)),
            sku_id="sku",
            session_id="sess",
            garment_category="saree",
        )
    )
    payload = posted[0]["json"]
    assert payload["category"] == "one-pieces"
    assert "prompt" not in payload
