/**
 * Kiosk capture rules that match ai_service person preprocess rejects.
 */

export const CAPTURE_RULES: readonly string[] = [
  "One person, looking toward the camera",
  "Face clear — no hands, phone, or scarf covering it",
  "Soft, even light on the face; avoid strong backlight",
  "Leave space around the head; don’t crop the chin or hairline",
  "Show shoulders and torso — not just a tight selfie crop",
];

export const CAPTURE_HEADLINE =
  "A clear front-facing still is all we need. If the face is hidden, the look can’t be styled.";

export const CAMERA_INSTRUCTION =
  "Fit your head in the oval and keep shoulders in frame. Hands and phones off the face.";
