"""Standardize a customer still before any try-on vendor generate.

Pipeline (CPU, milliseconds–low hundreds of ms; Pillow plus optional OpenCV):

1. Decode and apply EXIF orientation.
2. Detect a face via an injectable ``FaceDetector``. Default prefers OpenCV
   YuNet when the ONNX weights are present, else Haar. Pin
   ``opencv-python-headless`` to 4.x: OpenCV 5 removed ``CascadeClassifier``
   and Haar XMLs, which made every still fail closed as "no face". If OpenCV
   is missing or Haar/YuNet cannot load, detection returns None (fails closed).
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
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps

from app.settings import settings

FaceBox = tuple[int, int, int, int]

# Full-length sari / studio stills: face is often ~5–8% of min(width, height).
_MIN_FACE_FRACTION = 0.04
_YUNET_MODEL_PATH = (
    Path(__file__).resolve().parent / "assets" / "face_detection_yunet_2023mar.onnx"
)
_HAAR_CASCADE_FILES = (
    "haarcascade_frontalface_default.xml",
    "haarcascade_profileface.xml",
)
_HAAR_RETRY_CASCADE_FILES = (
    "haarcascade_frontalface_default.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_profileface.xml",
)
_EDGE_MARGIN_FRACTION = 0.02
_FACE_HEIGHT_IN_PORTRAIT = 0.14
_HEAD_CENTER_Y_FRACTION = 0.18
_CANONICAL_WIDTH_OVER_HEIGHT = 2 / 3
_MAX_OUTPUT = (1280, 1920)
_LOW_CONTRAST_SPAN = 12
_SECOND_FACE_AREA_RATIO = 0.45
_NMS_IOU = 0.3
_NMS_INTERSECTION_OVER_SMALLER = 0.5
_NMS_CENTER_DISTANCE_FRACTION = 0.55
_TORSO_ALIGN_FRACTION = 1.15
_TORSO_CHIN_SLACK_FRACTION = 0.2
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


class OpenCvYunetFaceDetector:
    """YuNet (FaceDetectorYN). Used when the ONNX file is present on disk."""

    def detect_face(self, image: Image.Image) -> FaceBox | None:
        """Return the highest-scoring face, or None."""
        faces = self.detect_faces(image)
        return None if not faces else faces[0]

    def detect_faces(self, image: Image.Image) -> list[FaceBox]:
        """Return YuNet boxes, largest first."""
        boxes = self._collect_yunet_boxes(image)
        unique = _unique_face_boxes(boxes)
        return sorted(unique, key=lambda box: box[2] * box[3], reverse=True)

    def _collect_yunet_boxes(self, image: Image.Image) -> list[FaceBox]:
        """Run YuNet on the full frame, then the upper body if nothing matches."""
        import cv2
        import numpy as np

        if not hasattr(cv2, "FaceDetectorYN_create") or not _YUNET_MODEL_PATH.is_file():
            return []
        rgb = np.asarray(image.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        boxes = _yunet_detect(bgr)
        if boxes:
            return boxes
        upper_h = max(1, int(bgr.shape[0] * 0.55))
        return _yunet_detect(bgr[:upper_h, :, :])


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
        """Run Haar; retry CLAHE and an upper-body crop for small/full-length faces."""
        import cv2
        import numpy as np

        if not hasattr(cv2, "CascadeClassifier"):
            return []
        rgb = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        min_side = min(gray.shape[0], gray.shape[1])
        first = _haar_detect_on_gray(
            gray,
            cascade_names=_HAAR_CASCADE_FILES,
            scale_factor=1.1,
            min_neighbors=5,
            min_size=max(24, int(0.04 * min_side)),
        )
        if first:
            return first
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        retry_min = max(20, int(0.025 * min_side))
        second = _haar_detect_on_gray(
            clahe,
            cascade_names=_HAAR_RETRY_CASCADE_FILES,
            scale_factor=1.05,
            min_neighbors=3,
            min_size=retry_min,
        )
        if second:
            return second
        upper_h = max(1, int(gray.shape[0] * 0.55))
        return _haar_detect_on_gray(
            gray[:upper_h, :],
            cascade_names=_HAAR_RETRY_CASCADE_FILES,
            scale_factor=1.05,
            min_neighbors=3,
            min_size=retry_min,
        )


class UnavailableFaceDetector:
    """Used when OpenCV is not installed. Always reports no face."""

    def detect_face(self, image: Image.Image) -> FaceBox | None:
        """Return None so production fails closed unless stub passthrough applies."""
        return None

    def detect_faces(self, image: Image.Image) -> list[FaceBox]:
        """No faces when OpenCV is unavailable."""
        return []


def default_face_detector() -> FaceDetector:
    """Prefer YuNet when weights exist; else Haar; else fail closed."""
    try:
        import cv2
    except ImportError:
        return UnavailableFaceDetector()
    yunet_ready = hasattr(cv2, "FaceDetectorYN_create") and _yunet_weights_present()
    if yunet_ready:
        return OpenCvYunetFaceDetector()
    if hasattr(cv2, "CascadeClassifier"):
        return OpenCvHaarFaceDetector()
    return UnavailableFaceDetector()


def _yunet_weights_present() -> bool:
    """True when the YuNet ONNX file is on disk and is not a Git LFS pointer."""
    if not _YUNET_MODEL_PATH.is_file():
        return False
    return _YUNET_MODEL_PATH.stat().st_size > 10_000


def _yunet_detect(bgr_image) -> list[FaceBox]:
    """Run FaceDetectorYN on a BGR ndarray; return (x, y, w, h) boxes."""
    import cv2

    height, width = bgr_image.shape[:2]
    if width < 8 or height < 8:
        return []
    detector = cv2.FaceDetectorYN_create(
        str(_YUNET_MODEL_PATH),
        "",
        (width, height),
        0.6,
        0.3,
        5000,
    )
    _faces_ok, faces = detector.detect(bgr_image)
    if faces is None or len(faces) == 0:
        return []
    boxes: list[FaceBox] = []
    for row in faces:
        left, top, box_w, box_h = (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        if box_w >= 8 and box_h >= 8:
            boxes.append((left, top, box_w, box_h))
    return boxes


def _haar_detect_on_gray(
    gray,
    *,
    cascade_names: tuple[str, ...],
    scale_factor: float,
    min_neighbors: int,
    min_size: int,
) -> list[FaceBox]:
    """Run named Haar cascades on a single-channel image."""
    import cv2

    found_boxes: list[FaceBox] = []
    side = max(8, int(min_size))
    for name in cascade_names:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        if cascade.empty():
            continue
        found = cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=(side, side),
        )
        found_boxes.extend((int(x), int(y), int(w), int(h)) for x, y, w, h in found)
    return found_boxes


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
    """Reject a still when a second distinct large face is present.

    Haar often returns duplicate boxes on one face plus jewelry/watermark
    blobs on the torso. Those must not count as a second person.
    """
    boxes = _unique_face_boxes(_detected_faces(detector, image))
    primary_area = max(1, primary[2] * primary[3])
    for box in boxes:
        if _boxes_are_same_face(box, primary):
            continue
        if _is_torso_false_positive(primary, box):
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
    """NMS: keep largest boxes; drop overlapping, nested, or tightly-centered duplicates."""
    unique: list[FaceBox] = []
    ordered = sorted(boxes, key=lambda box: box[2] * box[3], reverse=True)
    for box in ordered:
        if any(_boxes_are_same_face(box, kept) for kept in unique):
            continue
        unique.append(box)
    return unique


def _boxes_are_same_face(left: FaceBox, right: FaceBox) -> bool:
    """True when two Haar/YuNet boxes describe the same face, not two people."""
    if left == right:
        return True
    if _boxes_overlap(left, right) >= _NMS_IOU:
        return True
    if _intersection_over_smaller(left, right) >= _NMS_INTERSECTION_OVER_SMALLER:
        return True
    left_cx = left[0] + left[2] / 2
    left_cy = left[1] + left[3] / 2
    right_cx = right[0] + right[2] / 2
    right_cy = right[1] + right[3] / 2
    distance = ((left_cx - right_cx) ** 2 + (left_cy - right_cy) ** 2) ** 0.5
    scale = max(max(left[2], left[3]), max(right[2], right[3]))
    return distance < _NMS_CENTER_DISTANCE_FRACTION * scale


def _is_torso_false_positive(primary: FaceBox, box: FaceBox) -> bool:
    """True for jewelry, sari-fold, and watermark blobs under the chin, in-line with the face."""
    primary_cx = primary[0] + primary[2] / 2
    box_cx = box[0] + box[2] / 2
    chin_y = primary[1] + primary[3]
    aligned = abs(box_cx - primary_cx) <= max(primary[2], box[2]) * _TORSO_ALIGN_FRACTION
    below_chin = box[1] >= chin_y - int(_TORSO_CHIN_SLACK_FRACTION * primary[3])
    return aligned and below_chin


def _intersection_area(left: FaceBox, right: FaceBox) -> int:
    """Return overlapping pixel area of two (x, y, w, h) boxes."""
    ax, ay, aw, ah = left
    bx, by, bw, bh = right
    inter_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    inter_h = max(0, min(ay + ah, by + bh) - max(ay, by))
    return inter_w * inter_h


def _intersection_over_smaller(left: FaceBox, right: FaceBox) -> float:
    """Return intersection over the smaller box area (catches nested Haar hits)."""
    inter = _intersection_area(left, right)
    smaller = min(left[2] * left[3], right[2] * right[3])
    return 0.0 if smaller <= 0 else inter / smaller


def _boxes_overlap(left: FaceBox, right: FaceBox) -> float:
    """Return intersection-over-union for two (x, y, w, h) boxes."""
    inter = _intersection_area(left, right)
    union = left[2] * left[3] + right[2] * right[3] - inter
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
