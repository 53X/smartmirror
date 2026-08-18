"""OpenAI Images edit — dress the person in the described garment, keep identity."""

from __future__ import annotations

import base64
from io import BytesIO

import httpx
from PIL import Image
from smartmirror_shared.logging_config import configure_service_logging, safe_event

from app.settings import settings
from app.tryon.garment_prompt import compose_tryon_prompt
from app.tryon.identity_mask import build_identity_lock_mask
from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor

logger = configure_service_logging("ai_service", settings.log_level)


class OpenAITryOnVendor(TryOnVendor):
    """Use gpt-image-1 edits with a clothing mask so identity stays and outfit changes."""

    @property
    def name(self) -> str:
        return "openai_gpt_image"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Call Images edits with person, garment, and an identity-lock mask."""
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        if request.face_box is None:
            raise RuntimeError("OpenAI try-on requires a detected face box for the identity mask")
        customer, face_box = _as_png(request.customer_still, request.face_box)
        garment, _ = _as_png(request.reconstructed_sari, None)
        with Image.open(BytesIO(customer)) as customer_image:
            mask_png = build_identity_lock_mask(
                customer_image.width,
                customer_image.height,
                face_box,
            )
            width, height = customer_image.width, customer_image.height
        prompt = compose_tryon_prompt(
            clothing_description=request.clothing_description or "the garment from the product image",
            garment_category=request.garment_category or "other",
        )
        data = {
            "model": settings.openai_tryon_model,
            "prompt": prompt,
            "size": "1024x1536",
            "quality": "high",
            "input_fidelity": "high",
        }
        files_with_mask = [
            ("image[]", ("customer.png", customer, "image/png")),
            ("image[]", ("garment.png", garment, "image/png")),
            ("mask", ("mask.png", mask_png, "image/png")),
        ]
        response = _post_edits(data, files_with_mask)
        if response.status_code >= 400:
            logger.warning(
                "openai_tryon_mask_retry %s",
                safe_event(
                    {
                        "http_status": response.status_code,
                        "body": response.text[:300],
                        "width": width,
                        "height": height,
                        "face_box": face_box,
                    }
                ),
            )
            retry_mask = build_identity_lock_mask(width, height, face_box, blur=False)
            files_retry = [
                ("image[]", ("customer.png", customer, "image/png")),
                ("image[]", ("garment.png", garment, "image/png")),
                ("mask", ("mask.png", retry_mask, "image/png")),
            ]
            response = _post_edits(data, files_retry)
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


def _as_png(
    payload: bytes,
    face_box: tuple[int, int, int, int] | None,
) -> tuple[bytes, tuple[int, int, int, int]]:
    """Normalize any still to PNG so the edits endpoint accepts it.

    Remaps ``face_box`` if the still is thumbnailed so the identity mask stays aligned.
    """
    image = Image.open(BytesIO(payload)).convert("RGB")
    original_w, original_h = image.size
    image.thumbnail((1280, 1920), Image.Resampling.LANCZOS)
    mapped = face_box or (0, 0, 0, 0)
    if face_box is not None and (image.width != original_w or image.height != original_h):
        scale_x = image.width / original_w
        scale_y = image.height / original_h
        left, top, box_w, box_h = face_box
        mapped = (
            int(left * scale_x),
            int(top * scale_y),
            max(1, int(box_w * scale_x)),
            max(1, int(box_h * scale_y)),
        )
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), mapped
