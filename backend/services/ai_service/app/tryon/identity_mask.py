"""Identity-lock mask for Stage B: keep the face, replace clothing."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter


def build_identity_lock_mask(width: int, height: int) -> bytes:
    """
    Return a PNG mask for OpenAI image edits.

    Opaque pixels are preserved (face and hair). Transparent pixels are the
    clothing/body region the model must replace with the sari.
    """
    if width < 8 or height < 8:
        raise ValueError("Mask size is too small")
    mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    center_x = width / 2
    center_y = height * 0.16
    radius_x = width * 0.18
    radius_y = height * 0.12
    draw.ellipse(
        (
            center_x - radius_x,
            center_y - radius_y,
            center_x + radius_x,
            center_y + radius_y,
        ),
        fill=(255, 255, 255, 255),
    )
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=max(2, int(width * 0.01))))
    buffer = BytesIO()
    blurred.save(buffer, format="PNG")
    return buffer.getvalue()


def mask_alpha_at(mask_png: bytes, x: int, y: int) -> int:
    """Return the alpha value at a pixel, for tests."""
    with Image.open(BytesIO(mask_png)) as image:
        return image.convert("RGBA").getpixel((x, y))[3]
