"""Tests for the identity-lock clothing mask."""

from app.tryon.identity_mask import build_identity_lock_mask, mask_alpha_at


def test_identity_lock_mask_keeps_face_and_edits_torso() -> None:
    width, height = 200, 400
    mask_png = build_identity_lock_mask(width, height)
    face_alpha = mask_alpha_at(mask_png, width // 2, int(height * 0.16))
    torso_alpha = mask_alpha_at(mask_png, width // 2, int(height * 0.55))
    assert face_alpha > 200
    assert torso_alpha < 40
