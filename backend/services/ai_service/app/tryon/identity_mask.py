"""Identity-lock mask for Stage B: keep face, pose, and background; edit clothing."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

FaceBox = tuple[int, int, int, int]


def build_identity_lock_mask(
    width: int,
    height: int,
    face_box: FaceBox,
    *,
    blur: bool = True,
) -> bytes:
    """
    Return a PNG mask for OpenAI image edits from a detected face box.

    Opaque pixels are preserved (face, hair halo, background, framing).
    Transparent pixels are the garment region below the chin that the model
    must replace with the sari. Coordinates are in the preprocessed still.
    """
    if width < 8 or height < 8:
        raise ValueError("Mask size is too small")
    left, top, box_w, box_h = face_box
    if box_w < 1 or box_h < 1:
        raise ValueError("Face box is too small to build an identity mask")

    mask = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(mask)
    garment = _garment_edit_box(width, height, face_box)
    draw.rounded_rectangle(garment, radius=max(8, box_w // 4), fill=(0, 0, 0, 0))

    halo_up = int(box_h * 0.35)
    halo_side = int(box_w * 0.30)
    halo_down = int(box_h * 0.12)
    face_ellipse = (
        max(0, left - halo_side),
        max(0, top - halo_up),
        min(width, left + box_w + halo_side),
        min(height, top + box_h + halo_down),
    )
    draw.ellipse(face_ellipse, fill=(255, 255, 255, 255))

    if blur:
        radius = max(2, int(min(width, height) * 0.012))
        mask = mask.filter(ImageFilter.GaussianBlur(radius=radius))
    buffer = BytesIO()
    mask.save(buffer, format="PNG")
    return buffer.getvalue()


def _garment_edit_box(
    width: int,
    height: int,
    face_box: FaceBox,
) -> tuple[int, int, int, int]:
    """Return a torso/drape rectangle that starts below the chin and stays on-canvas."""
    left, top, box_w, box_h = face_box
    center_x = left + box_w / 2
    chin_y = top + box_h
    hole_top = min(height - 8, chin_y + int(box_h * 0.08))
    hole_bottom = min(height - 4, max(hole_top + box_h * 2, int(height * 0.92)))
    half_width = max(int(box_w * 1.55), int(width * 0.28))
    hole_left = max(4, int(center_x - half_width))
    hole_right = min(width - 4, int(center_x + half_width))
    if hole_right - hole_left < 16:
        hole_left = max(4, width // 2 - 24)
        hole_right = min(width - 4, width // 2 + 24)
    if hole_bottom - hole_top < 16:
        hole_bottom = min(height - 4, hole_top + 24)
    return (hole_left, hole_top, hole_right, hole_bottom)


def mask_alpha_at(mask_png: bytes, x: int, y: int) -> int:
    """Return the alpha value at a pixel, for tests."""
    with Image.open(BytesIO(mask_png)) as image:
        return image.convert("RGBA").getpixel((x, y))[3]
