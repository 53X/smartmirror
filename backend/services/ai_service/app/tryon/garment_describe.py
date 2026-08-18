"""Step 1 clothing recognition: garment image only via OpenAI vision."""

from __future__ import annotations

import base64

import httpx
from smartmirror_shared.logging_config import configure_service_logging, safe_event

from app.settings import settings
from app.tryon.garment_prompt import DESCRIBE_PROMPT, sanitize_clothing_description

logger = configure_service_logging("ai_service", settings.log_level)

_FALLBACK_DESCRIPTION = "the garment from the product image"
_VISION_MODEL = "gpt-4o-mini"


def describe_garment(image_bytes: bytes) -> str:
    """Send only the garment image to OpenAI vision; never send the person still.

    If OPENAI_API_KEY is missing or the call fails, return a sanitized fallback
    and log a safe event (no image bytes).
    """
    fallback = sanitize_clothing_description(_FALLBACK_DESCRIPTION)
    if not settings.openai_api_key:
        logger.info("garment_describe_skipped %s", safe_event({"reason": "missing_openai_api_key"}))
        return fallback
    try:
        mime = _image_mime(image_bytes)
        data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        with httpx.Client(timeout=min(settings.tryon_vendor_timeout_seconds, 60)) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": _VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": DESCRIBE_PROMPT},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                    "max_tokens": 80,
                },
            )
        if response.status_code >= 400:
            logger.warning(
                "garment_describe_failed %s",
                safe_event({"http_status": response.status_code, "body": response.text[:200]}),
            )
            return fallback
        content = ((response.json().get("choices") or [{}])[0].get("message") or {}).get("content")
        if not isinstance(content, str):
            logger.warning("garment_describe_failed %s", safe_event({"reason": "empty_content"}))
            return fallback
        return sanitize_clothing_description(content)
    except Exception as exc:
        logger.warning(
            "garment_describe_failed %s",
            safe_event({"reason": type(exc).__name__}),
        )
        return fallback


def _image_mime(image_bytes: bytes) -> str:
    """Guess PNG vs JPEG from magic bytes; default to PNG."""
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return "image/png"
