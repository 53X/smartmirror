/**
 * Capture SOP part types mirrored from the backend shared package.
 */
export const REQUIRED_PART_TYPES = [
  "full_hanging",
  "pallu",
  "body_field",
  "border",
  "blouse",
] as const;

export const OPTIONAL_PART_TYPES = [
  "pallu_end_border",
  "blouse_back",
  "colour_card",
] as const;

export const PART_TYPE_LABELS: Record<string, string> = {
  full_hanging: "Full sari hanging or laid out (this is the try-on garment)",
  pallu: "Pallu — decorative end, motif must be readable",
  body_field: "Body / field cloth (the metres that wrap the torso and legs)",
  border: "Running border (zari/motif repeat along the long edge)",
  blouse: "Blouse piece, or mark that the customer keeps her own",
  pallu_end_border: "Pallu end-border close-up",
  blouse_back: "Blouse back or neckline",
  colour_card: "Colour card + ruler",
};

export type RequiredPartType = (typeof REQUIRED_PART_TYPES)[number];
