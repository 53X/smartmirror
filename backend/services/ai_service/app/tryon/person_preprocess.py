"""Standardize a customer still before any try-on vendor generate.

Pipeline (CPU, milliseconds–low hundreds of ms; Pillow plus optional OpenCV):

1. Decode and apply EXIF orientation.
2. Detect a face via an injectable ``FaceDetector``. Default is OpenCV Haar
   when ``opencv-python-headless`` is installed. If OpenCV is missing, detection
   returns None (fails closed in production).
3. Crop to a canonical 2:3 portrait from the face, without stretching. If the
   crop would clip the face, expand the canvas with edge fill — never cut the face.
4. Mild luminance autolevel. No beauty filter and no identity reshape.
5. Reject unusable stills: no face, face too small, face too close to the edge,
   very low-contrast face, a second large face, or a hand/object covering the face.
6. Messy background is mitigated by cropping to the person. This module does not
   matte or replace the background (rembg is not a dependency).

Stub path: when the detector returns None **and** ``settings.tryon_allow_stub``
is True, preprocess no-ops (decoded PNG unchanged) and sets flag
``stub_passthrough``. Production (stub disabled) never uses a hardcoded y=16%
ellipse; it fails closed with a user-safe ValueError.

Do not log image bytes. Callers should emit ``safe_event`` metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Protocol

from PIL import Image, ImageOps

from app.settings import settings

FaceBox = tuple[int, int, int, int]

_MIN_FACE_FRACTION = 0.08
_EDGE_MARGIN_FRACTION = 0.02
_FACE_HEIGHT_IN_PORTRAIT = 0.14
_HEAD_CENTER_Y_FRACTION = 0.18
_CANONICAL_WIDTH_OVER_HEIGHT = 2 / 3
_MAX_OUTPUT = (1280, 1920)
_LOW_CONTRAST_SPAN = 12
_SECOND_FACE_AREA_RATIO = 0.45
_OCCLUSION_DARK_DELTA = 40
_OCCLUSION_COVER_VARIANCE = 18


class FaceDetector(Protocol):
    """Return (x, y, w, h) in image pixels, or None if no face is found."""

    def detect_face(self, image: Image.Image) -> FaceBox | None:
        """Detect the primary face box."""


@dataclass(frozen=True)
class PreprocessMetadata:
    """Geometry of the standardized still. Safe to log (no pixels)."""

    width: int
    height: int
    face_box: FaceBox | None
    crop_box: tuple[int, int, int, int]
    flags: tuple[str, ...] = field(default_factory=tuple)


class OpenCvHaarFaceDetector:
    """Haar cascade detector. Optional at import time; constructed only if cv2 loads."""

    def detect_face(self, image: Image.Image) -> FaceBox | None:
        """Return the largest frontal or profile face, or None."""
        faces = self.detect_faces(image)
        return None if not faces else faces[0]

    def detect_faces(self, image: Image.Image) -> list[FaceBox]:
        """Return Haar matches, largest first."""
        boxes = self._collect_haar_boxes(image)
        unique = _unique_face_boxes(boxes)
        return sorted(unique, key=lambda box: box[2] * box[3], reverse=True)

    def _collect_haar_boxes(self, image: Image.Image) -> list[FaceBox]:
        """Run frontal and profile cascades."""
        import cv2
        import numpy as np

        if not hasattr(cv2, "CascadeClassifier"):
            return []
        rgb = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        found_boxes: list[FaceBox] = []
        for name in (
            "haarcascade_frontalface_default.xml",
            "haarcascade_profileface.xml",
        ):
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
            if cascade.empty():
                continue
            found = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(24, 24),
            )
            found_boxes.extend((int(x), int(y), int(w), int(h)) for x, y, w, h in found)
        return found_boxes


class UnavailableFaceDetector:
    """Used when OpenCV is not installed. Always reports no face."""

    def detect_face(self, image: Image.Image) -> FaceBox | None:
        """Return None so production fails closed unless stub passthrough applies."""
        return None

    def detect_faces(self, image: Image.Image) -> list[FaceBox]:
        """No faces when OpenCV is unavailable."""
        return []


def default_face_detector() -> FaceDetector:
    """Prefer Haar; fall back to a detector that always returns None."""
    try:
        import cv2
    except ImportError:
        return UnavailableFaceDetector()
    if not hasattr(cv2, "CascadeClassifier"):
        return UnavailableFaceDetector()
    return OpenCvHaarFaceDetector()


def preprocess_person_still(
    image_bytes: bytes,
    *,
    detector: FaceDetector | None = None,
) -> tuple[bytes, PreprocessMetadata]:
    """
    Return a standardized person PNG and crop/face metadata.

    Raises:
        ValueError: still is unusable (no face, too small, clipped, low contrast,
            extra person, or face covered) unless stub passthrough applies.
    """
    image = _decode_oriented_rgb(image_bytes)
    chosen = detector if detector is not None else default_face_detector()
    face_box = chosen.detect_face(image)

    if face_box is None:
        if settings.tryon_allow_stub:
            png = _to_png(image)
            return png, PreprocessMetadata(
                width=image.width,
                height=image.height,
                face_box=None,
                crop_box=(0, 0, image.width, image.height),
                flags=("stub_passthrough", "no_face"),
            )
        raise ValueError(
            "No face detected in the customer still. Recapture with your face clearly visible."
        )

    _reject_unusable_face(image, face_box)
    _reject_extra_faces(chosen, image, face_box)
    _reject_face_occlusion(image, face_box)
    cropped, out_face, crop_box, flags = _portrait_crop_from_face(image, face_box)
    leveled, level_flags = _autolevel_luminance(cropped)
    flags = flags + level_flags
    scaled, out_face = _fit_max_output(leveled, out_face)
    png = _to_png(scaled)
    return png, PreprocessMetadata(
        width=scaled.width,
        height=scaled.height,
        face_box=out_face,
        crop_box=crop_box,
        flags=tuple(flags),
    )


def _decode_oriented_rgb(image_bytes: bytes) -> Image.Image:
    """Decode bytes and honor EXIF orientation."""
    with Image.open(BytesIO(image_bytes)) as raw:
        oriented = ImageOps.exif_transpose(raw)
        working = oriented if oriented is not None else raw
        return working.convert("RGB")


def _reject_unusable_face(image: Image.Image, face_box: FaceBox) -> None:
    """Raise ValueError for faces that cannot support a reliable try-on."""
    left, top, width, height = face_box
    min_side = min(image.width, image.height)
    if min(width, height) < _MIN_FACE_FRACTION * min_side:
        raise ValueError(
            "Face is too small in the frame. Step closer or recapture."
        )
    margin = max(4, int(_EDGE_MARGIN_FRACTION * min_side))
    if (
        left < margin
        or top < margin
        or left + width > image.width - margin
        or top + height > image.height - margin
    ):
        raise ValueError(
            "Face is too close to the edge of the photo. Recapture with more space around your head."
        )
    pad_x = max(2, int(width * 0.2))
    pad_y = max(2, int(height * 0.2))
    sample = (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(image.width, left + width + pad_x),
        min(image.height, top + height + pad_y),
    )
    face_region = image.crop(sample)
    gray = face_region.convert("L")
    histogram = gray.histogram()
    low = _percentile_from_histogram(histogram, 5)
    high = _percentile_from_histogram(histogram, 95)
    if high - low < _LOW_CONTRAST_SPAN:
        raise ValueError(
            "Face region contrast is too low. Recapture in even lighting."
        )


def _reject_extra_faces(
    detector: FaceDetector,
    image: Image.Image,
    primary: FaceBox,
) -> None:
    """Reject a still when a second face is large enough to compete with the subject."""
    boxes = _detected_faces(detector, image)
    primary_area = max(1, primary[2] * primary[3])
    for box in boxes:
        if box == primary:
            continue
        if box[2] * box[3] >= _SECOND_FACE_AREA_RATIO * primary_area:
            raise ValueError(
                "More than one person is in the frame. Recapture with only the subject."
            )


def _reject_face_occlusion(image: Image.Image, face_box: FaceBox) -> None:
    """Reject a still when a hand, phone, or object covers a large part of the face.

    Uses luminance only (dark, low-variance cover vs the uncovered half). Do not
    gate on RGB skin-tone rules — that false-rejects darker complexions.
    """
    left, top, width, height = face_box
    mid = top + int(height * 0.45)
    upper = image.crop((left, top, left + width, max(top + 1, mid)))
    lower = image.crop((left, min(image.height, mid), left + width, top + height))
    if lower.width < 2 or lower.height < 2 or upper.width < 2 or upper.height < 2:
        return
    upper_luma = list(upper.convert("L").getdata())
    lower_luma = list(lower.convert("L").getdata())
    upper_mean = sum(upper_luma) / len(upper_luma)
    lower_mean = sum(lower_luma) / len(lower_luma)
    upper_var = _luma_variance(upper_luma)
    lower_var = _luma_variance(lower_luma)
    covered_lower = (
        upper_mean - lower_mean >= _OCCLUSION_DARK_DELTA
        and lower_var < _OCCLUSION_COVER_VARIANCE
    )
    covered_upper = (
        lower_mean - upper_mean >= _OCCLUSION_DARK_DELTA
        and upper_var < _OCCLUSION_COVER_VARIANCE
    )
    if covered_lower or covered_upper:
        raise ValueError(
            "Something is covering the face. Move hands, hair, and phones away and recapture."
        )


def _detected_faces(detector: FaceDetector, image: Image.Image) -> list[FaceBox]:
    """Use detect_faces when present; otherwise wrap detect_face."""
    detect_faces = getattr(detector, "detect_faces", None)
    if callable(detect_faces):
        return list(detect_faces(image))
    primary = detector.detect_face(image)
    return [] if primary is None else [primary]


def _unique_face_boxes(boxes: list[FaceBox]) -> list[FaceBox]:
    """Drop near-duplicate Haar hits from frontal + profile cascades."""
    unique: list[FaceBox] = []
    for box in boxes:
        if any(_boxes_overlap(box, kept) > 0.6 for kept in unique):
            continue
        unique.append(box)
    return unique


def _boxes_overlap(left: FaceBox, right: FaceBox) -> float:
    """Return intersection-over-union for two (x, y, w, h) boxes."""
    ax, ay, aw, ah = left
    bx, by, bw, bh = right
    inter_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    inter_h = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return 0.0 if union <= 0 else inter / union


def _luma_variance(samples: list[int]) -> float:
    """Return population variance of 8-bit luma samples."""
    if not samples:
        return 0.0
    mean = sum(samples) / len(samples)
    return sum((value - mean) ** 2 for value in samples) / len(samples)


def _portrait_crop_from_face(
    image: Image.Image,
    face_box: FaceBox,
) -> tuple[Image.Image, FaceBox, tuple[int, int, int, int], list[str]]:
    """Crop a 2:3 portrait with the head in the upper portion; pad rather than clip the face."""
    face_x, face_y, face_w, face_h = face_box
    crop_h = max(int(face_h / _FACE_HEIGHT_IN_PORTRAIT), face_h * 4)
    crop_w = int(crop_h * _CANONICAL_WIDTH_OVER_HEIGHT)
    halo = int(max(face_w, face_h) * 0.4)
    crop_w = max(crop_w, face_w + 2 * halo)
    crop_h = int(crop_w / _CANONICAL_WIDTH_OVER_HEIGHT)

    center_x = face_x + face_w / 2
    center_y = face_y + face_h / 2
    left = int(center_x - crop_w / 2)
    top = int(center_y - _HEAD_CENTER_Y_FRACTION * crop_h)
    right = left + crop_w
    bottom = top + crop_h

    if face_x < left:
        left = face_x
        right = left + crop_w
    if face_y < top:
        top = face_y
        bottom = top + crop_h
    if face_x + face_w > right:
        right = face_x + face_w
        left = right - crop_w
    if face_y + face_h > bottom:
        bottom = face_y + face_h
        top = bottom - crop_h

    pad_left = max(0, -left)
    pad_top = max(0, -top)
    pad_right = max(0, right - image.width)
    pad_bottom = max(0, bottom - image.height)
    flags: list[str] = []
    working = image
    origin_x = 0
    origin_y = 0
    if pad_left or pad_top or pad_right or pad_bottom:
        flags.append("edge_fill")
        fill = image.getpixel((0, 0))
        working = ImageOps.expand(
            image,
            border=(pad_left, pad_top, pad_right, pad_bottom),
            fill=fill,
        )
        origin_x = pad_left
        origin_y = pad_top
        left += pad_left
        top += pad_top
        right += pad_left
        bottom += pad_top
        face_x += pad_left
        face_y += pad_top

    cropped = working.crop((left, top, right, bottom))
    out_face = (face_x - left, face_y - top, face_w, face_h)
    if (
        out_face[0] < 0
        or out_face[1] < 0
        or out_face[0] + out_face[2] > cropped.width
        or out_face[1] + out_face[3] > cropped.height
    ):
        raise ValueError(
            "Could not frame the customer still without clipping the face. Recapture."
        )
    crop_box = (
        left - origin_x,
        top - origin_y,
        crop_w,
        crop_h,
    )
    return cropped, out_face, crop_box, flags


def _autolevel_luminance(image: Image.Image) -> tuple[Image.Image, list[str]]:
    """Percentile-stretch luminance; keep channel ratios so identity color is not inverted."""
    gray = image.convert("L")
    histogram = gray.histogram()
    low = _percentile_from_histogram(histogram, 2)
    high = _percentile_from_histogram(histogram, 98)
    if high <= low + 8:
        return image, ["low_contrast_skipped"]
    scale = 255.0 / (high - low)

    def _stretch(pixel: int) -> int:
        return int(max(0, min(255, (pixel - low) * scale)))

    lookup = bytes(_stretch(index) for index in range(256))
    return image.point(lookup * 3), ["autolevel"]


def _fit_max_output(image: Image.Image, face_box: FaceBox) -> tuple[Image.Image, FaceBox]:
    """Downscale to the vendor max size without stretching; remap the face box."""
    if image.width <= _MAX_OUTPUT[0] and image.height <= _MAX_OUTPUT[1]:
        return image, face_box
    original_w, original_h = image.width, image.height
    fitted = image.copy()
    fitted.thumbnail(_MAX_OUTPUT, Image.Resampling.LANCZOS)
    scale_x = fitted.width / original_w
    scale_y = fitted.height / original_h
    left, top, width, height = face_box
    scaled_box = (
        int(left * scale_x),
        int(top * scale_y),
        max(1, int(width * scale_x)),
        max(1, int(height * scale_y)),
    )
    return fitted, scaled_box


def _percentile_from_histogram(histogram: list[int], percentile: float) -> int:
    """Return the intensity at a cumulative histogram percentile."""
    total = sum(histogram) or 1
    target = total * (percentile / 100.0)
    cumulative = 0
    for index, count in enumerate(histogram):
        cumulative += count
        if cumulative >= target:
            return index
    return 255


def _to_png(image: Image.Image) -> bytes:
    """Encode RGB as PNG bytes."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
