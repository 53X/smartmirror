"""Tests for the identity-lock clothing mask (face-box geometry, not a fixed ellipse)."""

from app.tryon.identity_mask import build_identity_lock_mask, mask_alpha_at


def test_identity_lock_mask_tracks_lower_left_face_not_canonical_ellipse() -> None:
    """Opaque lock must follow an injected face, not a hardcoded y=16% ellipse."""
    width, height = 200, 400
    face_box = (16, 280, 48, 56)
    mask_png = build_identity_lock_mask(width, height, face_box)

    face_cx = face_box[0] + face_box[2] // 2
    face_cy = face_box[1] + face_box[3] // 2
    face_alpha = mask_alpha_at(mask_png, face_cx, face_cy)
    background_corner_alpha = mask_alpha_at(mask_png, width - 8, 8)

    assert face_alpha > 200
    assert background_corner_alpha > 200


def test_identity_lock_mask_keeps_pose_background_and_opens_garment_region() -> None:
    """Background and face stay locked; only the torso under the chin is editable."""
    width, height = 200, 400
    face_box = (76, 24, 48, 56)
    mask_png = build_identity_lock_mask(width, height, face_box)

    face_cx = face_box[0] + face_box[2] // 2
    face_cy = face_box[1] + face_box[3] // 2
    garment_x = face_cx
    garment_y = face_box[1] + face_box[3] + 40

    assert mask_alpha_at(mask_png, face_cx, face_cy) > 200
    assert mask_alpha_at(mask_png, 6, 6) > 200
    assert mask_alpha_at(mask_png, garment_x, garment_y) < 40


def test_identity_lock_mask_tracks_upper_center_face_and_edits_torso() -> None:
    """A centered-upper face stays locked; mid-torso stays editable."""
    width, height = 200, 400
    face_box = (76, 24, 48, 56)
    mask_png = build_identity_lock_mask(width, height, face_box)

    face_cx = face_box[0] + face_box[2] // 2
    face_cy = face_box[1] + face_box[3] // 2
    face_alpha = mask_alpha_at(mask_png, face_cx, face_cy)
    torso_alpha = mask_alpha_at(mask_png, width // 2, int(height * 0.62))

    assert face_alpha > 200
    assert torso_alpha < 40
