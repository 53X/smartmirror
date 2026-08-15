"""OpenAI Images edit — replace clothing with the sari, keep the same person."""

from __future__ import annotations

import base64
from io import BytesIO

import httpx
from PIL import Image
from smartmirror_shared.logging_config import configure_service_logging

from app.settings import settings
from app.tryon.identity_mask import build_identity_lock_mask
from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor

logger = configure_service_logging("ai_service", settings.log_level)

DRAPE_PROMPT = (
    "This is a virtual try-on. Image 1 is the person. Image 2 is the sari garment. "
    "REPLACE every garment the person is currently wearing with the sari from image 2. "
    "The subject must change: she cannot stay in her original clothes, jeans, dress, or top. "
    "Drape that exact sari in a traditional Nivi drape — pallu over the left shoulder, "
    "stacked waist pleats, blouse from the sari set if visible. "
    "Keep the SAME person: face, skin tone, hair, pose, body proportions, camera angle, background. "
    "Preserve the sari's exact pallu motif, border, colour, and weave. "
    "Photoreal fashion photograph. No text, no watermark, no collage, no floating fabric overlay."
)


class OpenAITryOnVendor(TryOnVendor):
    """Use gpt-image-1 edits with a clothing mask so identity stays and outfit changes."""

    @property
    def name(self) -> str:
        return "openai_gpt_image"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Call Images edits with person, sari, and an identity-lock mask."""
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        customer = _as_png(request.customer_still)
        garment = _as_png(request.reconstructed_sari)
        with Image.open(BytesIO(customer)) as customer_image:
            mask_png = build_identity_lock_mask(customer_image.width, customer_image.height)
        data = {
            "model": settings.openai_tryon_model,
            "prompt": DRAPE_PROMPT,
            "size": "1024x1536",
            "quality": "high",
            "input_fidelity": "high",
        }
        files_with_mask = [
            ("image[]", ("customer.png", customer, "image/png")),
            ("image[]", ("sari.png", garment, "image/png")),
            ("mask", ("mask.png", mask_png, "image/png")),
        ]
        response = _post_edits(data, files_with_mask)
        if response.status_code >= 400:
            logger.warning(
                "openai_tryon_mask_rejected status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            retry_data = {**data, "input_fidelity": "low"}
            response = _post_edits(retry_data, files_with_mask[:2])
        if response.status_code >= 400:
            raise RuntimeError(f"OpenAI try-on failed ({response.status_code}): {response.text[:500]}")
        items = (response.json().get("data") or [])
        if not items:
            raise RuntimeError("OpenAI returned no image")
        raw = _decode_image_payload(items[0])
        image = Image.open(BytesIO(raw)).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return TryOnResult(image_png=buffer.getvalue(), vendor_name=self.name)


def _post_edits(data: dict[str, str], files: list) -> httpx.Response:
    """POST /v1/images/edits. Does not log image bytes."""
    with httpx.Client(timeout=settings.tryon_vendor_timeout_seconds) as client:
        return client.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            data=data,
            files=files,
        )


def _decode_image_payload(item: dict) -> bytes:
    """Read b64_json or a hosted URL from an OpenAI image object."""
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        with httpx.Client(timeout=60) as client:
            return client.get(item["url"]).content
    raise RuntimeError("OpenAI image payload missing b64_json and url")


def _as_png(payload: bytes) -> bytes:
    """Normalize any still to PNG so the edits endpoint accepts it."""
    image = Image.open(BytesIO(payload)).convert("RGB")
    image.thumbnail((1280, 1920), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
