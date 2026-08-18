"""Step 1 clothing recognition uses garment image only."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from app.tryon.garment_describe import describe_garment
from app.tryon.garment_prompt import DESCRIBE_PROMPT

FALLBACK = "the garment from the product image"


def _tiny_png(color: tuple[int, int, int] = (40, 80, 160)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def test_describe_garment_sends_describe_prompt_and_image_not_person(monkeypatch) -> None:
    posts: list[dict[str, Any]] = []
    garment = _tiny_png()

    class _FakeClient:
        def __init__(self, timeout: object = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, headers: dict | None = None, json: dict | None = None):
            posts.append({"url": url, "json": json, "headers": headers})
            return _FakeResponse(
                200,
                payload={
                    "choices": [
                        {"message": {"content": "  'a blue floral dress'\n"}},
                    ]
                },
            )

    monkeypatch.setattr("app.tryon.garment_describe.httpx.Client", _FakeClient)
    monkeypatch.setattr("app.tryon.garment_describe.settings.openai_api_key", "sk-test-not-a-secret")

    phrase = describe_garment(garment)
    assert phrase == "a blue floral dress"
    assert len(posts) == 1
    body = posts[0]["json"]
    assert body["model"] == "gpt-4o-mini"
    content = body["messages"][0]["content"]
    texts = [part["text"] for part in content if part.get("type") == "text"]
    assert DESCRIBE_PROMPT in texts
    image_parts = [part for part in content if part.get("type") == "image_url"]
    assert len(image_parts) == 1
    data_url = image_parts[0]["image_url"]["url"]
    assert data_url.startswith("data:image/")
    dumped = str(body).lower()
    assert "person" not in dumped
    assert "customer" not in dumped


def test_describe_garment_http_500_returns_fallback(monkeypatch) -> None:
    class _FakeClient:
        def __init__(self, timeout: object = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, headers: dict | None = None, json: dict | None = None):
            return _FakeResponse(500, text="upstream error")

    monkeypatch.setattr("app.tryon.garment_describe.httpx.Client", _FakeClient)
    monkeypatch.setattr("app.tryon.garment_describe.settings.openai_api_key", "sk-test-not-a-secret")

    assert describe_garment(_tiny_png()) == FALLBACK


def test_describe_garment_missing_api_key_returns_fallback(monkeypatch) -> None:
    monkeypatch.setattr("app.tryon.garment_describe.settings.openai_api_key", "")
    assert describe_garment(_tiny_png()) == FALLBACK
