/**
 * Kiosk capture rules that match ai_service person preprocess rejects.
 */

export const CAPTURE_RULES: readonly string[] = [
  "One person only, looking toward the camera",
  "Face fully visible — no hands, phone, hair, or scarf over the face",
  "Even light on the face; avoid strong backlight and deep shadow",
  "Leave space around the head; do not crop the chin or hairline",
  "Stand far enough to show shoulders and torso, not just a selfie crop",
];

export const CAPTURE_HEADLINE =
  "Front-facing, face clear, one person. A rejected still cannot generate a look.";

export const CAMERA_INSTRUCTION =
  "Fit your head in the oval and keep shoulders in frame. Hands and phones off the face.";
