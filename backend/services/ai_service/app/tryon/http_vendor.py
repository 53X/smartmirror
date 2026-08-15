"""HTTP Stage B vendor adapter. URL and key come from env only."""

from io import BytesIO

import httpx
from PIL import Image

from app.settings import settings
from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor


class HttpTryOnVendor(TryOnVendor):
    """POST customer + reconstructed sari to a hosted virtual try-on API."""

    @property
    def name(self) -> str:
        return "hosted_http"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Call the configured vendor; raise if the response is not an image."""
        if not settings.tryon_vendor_url or not settings.tryon_vendor_api_key:
            raise RuntimeError("Hosted try-on vendor env is not configured")

        headers = {"Authorization": f"Bearer {settings.tryon_vendor_api_key}"}
        files = {
            "customer_still": ("customer.jpg", request.customer_still, "image/jpeg"),
            "garment": ("sari.png", request.reconstructed_sari, "image/png"),
        }
        data = {"sku_id": request.sku_id, "session_id": request.session_id}
        with httpx.Client(timeout=settings.tryon_vendor_timeout_seconds) as client:
            response = client.post(
                settings.tryon_vendor_url,
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise RuntimeError("Try-on vendor did not return an image")
            image = Image.open(BytesIO(response.content)).convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return TryOnResult(image_png=buffer.getvalue(), vendor_name=self.name)
