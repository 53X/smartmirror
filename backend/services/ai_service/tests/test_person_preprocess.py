"""Tests for person-still preprocess (injected detector, no network)."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.tryon.person_preprocess import (
    UnavailableFaceDetector,
    default_face_detector,
    preprocess_person_still,
)


class FakeFaceDetector:
    """Injectable detector so tests never need OpenCV or a real face."""

    def __init__(
        self,
        box: tuple[int, int, int, int] | None,
        extra_boxes: list[tuple[int, int, int, int]] | None = None,
    ) -> None:
        self._box = box
        self._extra = extra_boxes or []

    def detect_face(self, image: Image.Image) -> tuple[int, int, int, int] | None:
        return self._box

    def detect_faces(self, image: Image.Image) -> list[tuple[int, int, int, int]]:
        if self._box is None:
            return []
        return [self._box, *self._extra]


def _still_with_face(
    width: int,
    height: int,
    face_box: tuple[int, int, int, int],
    *,
    face_color: tuple[int, int, int] = (220, 170, 140),
    bg: tuple[int, int, int] = (36, 40, 52),
) -> bytes:
    """Build a synthetic RGB PNG with a high-contrast rectangle as the face."""
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    left, top, box_w, box_h = face_box
    draw.rectangle((left, top, left + box_w - 1, top + box_h - 1), fill=face_color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_preprocess_keeps_face_in_frame_and_portrait_aspect() -> None:
    face_box = (90, 36, 48, 60)
    still = _still_with_face(240, 360, face_box)
    png, meta = preprocess_person_still(still, detector=FakeFaceDetector(face_box))

    with Image.open(BytesIO(png)) as out:
        assert out.width / out.height == pytest.approx(2 / 3, rel=0.08)
        fx, fy, fw, fh = meta.face_box
        assert fx >= 0 and fy >= 0
        assert fx + fw <= out.width
        assert fy + fh <= out.height
        assert fy + fh / 2 < out.height * 0.45


def test_preprocess_lighting_does_not_invert_face_color() -> None:
    face_box = (80, 40, 50, 62)
    still = _still_with_face(
        220,
        340,
        face_box,
        face_color=(210, 150, 120),
        bg=(18, 18, 22),
    )
    png, meta = preprocess_person_still(still, detector=FakeFaceDetector(face_box))
    with Image.open(BytesIO(png)) as out:
        fx, fy, fw, fh = meta.face_box
        sample = out.getpixel((fx + fw // 2, fy + fh // 2))
    assert sample[0] > sample[2]
    assert sample[0] > 80


def test_preprocess_missing_face_raises(monkeypatch) -> None:
    from app.settings import settings

    monkeypatch.setattr(settings, "tryon_allow_stub", False)
    still = _still_with_face(200, 300, (70, 30, 40, 50))
    with pytest.raises(ValueError, match="face"):
        preprocess_person_still(still, detector=FakeFaceDetector(None))


def test_preprocess_face_too_small_raises() -> None:
    face_box = (90, 40, 8, 8)
    still = _still_with_face(240, 360, face_box)
    with pytest.raises(ValueError, match="small"):
        preprocess_person_still(still, detector=FakeFaceDetector(face_box))


def test_preprocess_accepts_full_body_scale_face() -> None:
    """Full-length stills have a small face vs frame; ~6% of min-side must still pass."""
    face_box = (110, 24, 16, 20)
    still = _still_with_face(240, 360, face_box)
    png, meta = preprocess_person_still(still, detector=FakeFaceDetector(face_box))
    assert meta.face_box is not None
    with Image.open(BytesIO(png)) as out:
        assert out.height > out.width


def test_default_face_detector_is_operational() -> None:
    """OpenCV must expose a working detector (YuNet and/or Haar), not a no-op."""
    detector = default_face_detector()
    assert not isinstance(detector, UnavailableFaceDetector)


def test_haar_detector_finds_no_face_on_blank_canvas() -> None:
    from app.tryon.person_preprocess import OpenCvHaarFaceDetector

    blank = Image.new("RGB", (320, 480), (245, 245, 245))
    assert OpenCvHaarFaceDetector().detect_face(blank) is None


def test_default_detector_rejects_blank_still(monkeypatch) -> None:
    from app.settings import settings

    monkeypatch.setattr(settings, "tryon_allow_stub", False)
    blank = Image.new("RGB", (320, 480), (245, 245, 245))
    buffer = BytesIO()
    blank.save(buffer, format="PNG")
    with pytest.raises(ValueError, match="No face detected"):
        preprocess_person_still(buffer.getvalue())


def test_preprocess_rejects_second_large_face() -> None:
    primary = (70, 36, 50, 62)
    other = (140, 40, 48, 58)
    still = _still_with_face(240, 360, primary)
    with pytest.raises(ValueError, match="one person"):
        preprocess_person_still(
            still,
            detector=FakeFaceDetector(primary, extra_boxes=[other]),
        )


def test_preprocess_allows_small_second_face() -> None:
    primary = (70, 36, 50, 62)
    other = (160, 50, 20, 24)
    still = _still_with_face(240, 360, primary)
    png, meta = preprocess_person_still(
        still,
        detector=FakeFaceDetector(primary, extra_boxes=[other]),
    )
    assert meta.face_box is not None
    with Image.open(BytesIO(png)) as out:
        assert out.height > out.width


def test_preprocess_accepts_darker_complexion() -> None:
    face_box = (80, 40, 50, 62)
    still = _still_with_face(
        220,
        340,
        face_box,
        face_color=(118, 72, 48),
        bg=(28, 30, 38),
    )
    png, meta = preprocess_person_still(still, detector=FakeFaceDetector(face_box))
    assert meta.face_box is not None
    with Image.open(BytesIO(png)) as out:
        fx, fy, fw, fh = meta.face_box
        sample = out.getpixel((fx + fw // 2, fy + fh // 2))
    assert sample[0] > sample[2]


def test_preprocess_rejects_hand_or_object_covering_lower_face() -> None:
    face_box = (80, 40, 56, 70)
    still = _still_with_face(240, 360, face_box)
    image = Image.open(BytesIO(still)).convert("RGB")
    draw = ImageDraw.Draw(image)
    left, top, box_w, box_h = face_box
    draw.rectangle(
        (left, top + int(box_h * 0.45), left + box_w - 1, top + box_h - 1),
        fill=(18, 16, 14),
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    with pytest.raises(ValueError, match="cover"):
        preprocess_person_still(buffer.getvalue(), detector=FakeFaceDetector(face_box))


def test_preprocess_rejects_object_covering_upper_face() -> None:
    face_box = (80, 40, 56, 70)
    still = _still_with_face(240, 360, face_box)
    image = Image.open(BytesIO(still)).convert("RGB")
    draw = ImageDraw.Draw(image)
    left, top, box_w, box_h = face_box
    draw.rectangle(
        (left, top, left + box_w - 1, top + int(box_h * 0.45) - 1),
        fill=(18, 16, 14),
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    with pytest.raises(ValueError, match="cover"):
        preprocess_person_still(buffer.getvalue(), detector=FakeFaceDetector(face_box))


def test_preprocess_stub_passthrough_when_no_face(monkeypatch) -> None:
    from app.settings import settings

    monkeypatch.setattr(settings, "tryon_allow_stub", True)
    still = _still_with_face(48, 48, (12, 8, 10, 12))
    png, meta = preprocess_person_still(still, detector=FakeFaceDetector(None))
    with Image.open(BytesIO(png)) as out:
        assert out.size == (48, 48)
    assert "stub_passthrough" in meta.flags
