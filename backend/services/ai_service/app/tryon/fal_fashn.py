"""fal.ai FASHN v1.6 — person photo + garment photo, not an overlay."""

from __future__ import annotations

import base64
from io import BytesIO

import httpx
from PIL import Image

from app.settings import settings
from app.tryon.garment_prompt import map_fashn_category
from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor

FASHN_ENDPOINT = "https://fal.run/fal-ai/fashn/tryon/v1.6"


def _data_uri(image_bytes: bytes) -> str:
    """Encode JPEG/PNG bytes as a data URI for the FASHN HTTP API."""
    kind = "image/jpeg" if image_bytes[:3] == b"\xff\xd8\xff" else "image/png"
    return f"data:{kind};base64,{base64.b64encode(image_bytes).decode('ascii')}"


class FalFashnVendor(TryOnVendor):
    """Drape the garment onto the customer via FASHN virtual try-on."""

    @property
    def name(self) -> str:
        return "fal_fashn_v1_6"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """POST model + garment images; return the first generated PNG."""
        if not settings.fal_key:
            raise RuntimeError("FAL_KEY is not set")
        payload = {
            "model_image": _data_uri(request.customer_still),
            "garment_image": _data_uri(request.reconstructed_sari),
            "category": map_fashn_category(request.garment_category),
            "mode": "quality",
            "garment_photo_type": "flat-lay",
            "output_format": "png",
            "num_samples": 1,
        }
        with httpx.Client(timeout=settings.tryon_vendor_timeout_seconds) as client:
            response = client.post(
                FASHN_ENDPOINT,
                headers={
                    "Authorization": f"Key {settings.fal_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        images = body.get("images") or []
        if not images:
            raise RuntimeError("FASHN returned no images")
        image_url = images[0].get("url")
        if not image_url:
            raise RuntimeError("FASHN image payload missing url")
        with httpx.Client(timeout=60) as client:
            image_response = client.get(image_url)
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content)).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return TryOnResult(image_png=buffer.getvalue(), vendor_name=self.name)
