"""Test-only overlay. Never the default product path."""

from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor


class StubTryOnVendor(TryOnVendor):
    """Placeholder compositor used until a hosted vendor wins the bake-off."""

    @property
    def name(self) -> str:
        return "stub"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Soft-light the canonical sari over the lower body; label as a look preview."""
        customer = Image.open(BytesIO(request.customer_still)).convert("RGBA")
        sari = Image.open(BytesIO(request.reconstructed_sari)).convert("RGBA")
        width = min(720, customer.width)
        height = int(customer.height * (width / customer.width))
        base = customer.resize((width, height), Image.Resampling.LANCZOS)
        overlay_h = int(height * 0.78)
        overlay_w = int(width * 0.62)
        draped = sari.resize((overlay_w, overlay_h), Image.Resampling.LANCZOS)
        faded = draped.copy()
        alpha = ImageEnhance.Brightness(faded.split()[-1]).enhance(0.55)
        faded.putalpha(alpha)
        dest_x = (width - overlay_w) // 2
        dest_y = int(height * 0.18)
        composed = Image.new("RGBA", base.size)
        composed.alpha_composite(base)
        composed.alpha_composite(faded, dest=(dest_x, dest_y))
        draw = ImageDraw.Draw(composed)
        font = ImageFont.load_default()
        draw.rectangle((16, height - 52, width - 16, height - 16), fill=(12, 10, 8, 200))
        draw.text(
            (28, height - 42),
            "How it would look  |  stub preview, not a live overlay",
            fill=(245, 230, 200, 255),
            font=font,
        )
        rgb = composed.convert("RGB")
        buffer = BytesIO()
        rgb.save(buffer, format="PNG")
        return TryOnResult(image_png=buffer.getvalue(), vendor_name=self.name)
