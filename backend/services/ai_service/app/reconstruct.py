"""Stage A: prefer a real hanging/draped sari photo over a part collage."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageEnhance
from smartmirror_shared.part_types import REQUIRED_PART_TYPES

CANVAS_SIZE = (768, 1408)

REGION_BOXES: dict[str, tuple[int, int, int, int]] = {
    "pallu": (48, 48, 720, 420),
    "border": (48, 1180, 720, 1360),
    "body_field": (80, 540, 688, 1240),
    "blouse": (240, 620, 528, 860),
    "full_hanging": (0, 0, 768, 1408),
}


def reconstruct_from_part_bytes(parts: dict[str, bytes]) -> bytes:
    """
    Build the garment image used for try-on.

    If a full hanging/draped sari shot exists, that IS the garment.
    A collage of crops is only a last resort and is a poor try-on input.
    """
    hanging = parts.get("full_hanging") or parts.get("full_drape")
    if hanging:
        return _normalize_garment(_open_rgb(hanging))

    missing = [part for part in REQUIRED_PART_TYPES if part not in parts]
    if missing:
        raise ValueError(f"Missing required part shots: {', '.join(missing)}")

    canvas = Image.new("RGBA", CANVAS_SIZE, (18, 16, 14, 255))
    for part_type, box in REGION_BOXES.items():
        payload = parts.get(part_type)
        if not payload or part_type == "full_hanging":
            continue
        _paste_cover(canvas, _open_rgb(payload), box, opacity=0.95)
    output = Image.new("RGB", CANVAS_SIZE, (18, 16, 14))
    output.paste(canvas, mask=canvas.split()[-1])
    return _to_png(output)


def _normalize_garment(image: Image.Image) -> bytes:
    """Resize a real sari photo to a tall garment canvas without covering labels."""
    rgb = image.convert("RGB")
    rgb.thumbnail((1024, 1536), Image.Resampling.LANCZOS)
    return _to_png(rgb)


def _open_rgb(payload: bytes) -> Image.Image:
    return Image.open(BytesIO(payload)).convert("RGBA")


def _paste_cover(
    canvas: Image.Image,
    source: Image.Image,
    box: tuple[int, int, int, int],
    opacity: float,
) -> None:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    fitted = _cover_resize(source, width, height)
    if opacity < 1:
        alpha = fitted.split()[-1]
        faded = ImageEnhance.Brightness(alpha).enhance(opacity)
        fitted.putalpha(faded)
    canvas.alpha_composite(fitted, dest=(left, top))


def _cover_resize(image: Image.Image, width: int, height: int) -> Image.Image:
    source_ratio = image.width / image.height
    target_ratio = width / height
    if source_ratio > target_ratio:
        new_height = height
        new_width = int(height * source_ratio)
    else:
        new_width = width
        new_height = int(width / source_ratio)
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = max((new_width - width) // 2, 0)
    top = max((new_height - height) // 2, 0)
    return resized.crop((left, top, left + width, top + height))


def _to_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()
