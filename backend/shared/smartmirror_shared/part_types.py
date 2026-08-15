"""Canonical sari part-shot types used by staff capture and Stage A reconstruct."""

from typing import Final

# Five shots that actually matter for a showroom SKU.
# Try-on uses `full_hanging` (or a draped product photo) as the garment.
# The other four lock identity so the model cannot invent a different sari.
REQUIRED_PART_TYPES: Final[tuple[str, ...]] = (
    "full_hanging",
    "pallu",
    "body_field",
    "border",
    "blouse",
)

OPTIONAL_PART_TYPES: Final[tuple[str, ...]] = (
    "pallu_end_border",
    "blouse_back",
    "colour_card",
)

ALL_PART_TYPES: Final[tuple[str, ...]] = REQUIRED_PART_TYPES + OPTIONAL_PART_TYPES

PART_TYPE_LABELS: Final[dict[str, str]] = {
    "full_hanging": "Full sari hanging or laid out (this is the try-on garment)",
    "pallu": "Pallu — decorative end, motif must be readable",
    "body_field": "Body / field cloth (the metres that wrap the torso and legs)",
    "border": "Running border (zari/motif repeat along the long edge)",
    "blouse": "Blouse piece, or mark that the customer keeps her own",
    "pallu_end_border": "Pallu end-border close-up",
    "blouse_back": "Blouse back or neckline",
    "colour_card": "Colour card + ruler",
}


def is_known_part_type(part_type: str) -> bool:
    """Return True when the part type is in the v1 capture SOP."""
    return part_type in ALL_PART_TYPES
