"""Garment-agnostic Step 1 describe prompt and Step 2 try-on composition."""

from __future__ import annotations

import re

DESCRIBE_PROMPT = (
    "Describe this clothing item in a short phrase. "
    "For example: 'a blue floral dress', 'a red plaid flannel shirt', "
    "'navy tailored trousers', 'a black leather jacket'. "
    "Name colour, pattern, and garment type only. "
    "This is a product photo of clothing only — do not mention any human subject."
)

_FALLBACK_DESCRIPTION = "the garment from the product image"
_MAX_DESCRIPTION_LENGTH = 120
_VALID_CATEGORIES = frozenset({"tops", "bottoms", "one-pieces", "saree", "other"})
_FASHN_CATEGORIES = frozenset({"tops", "bottoms", "one-pieces"})
_INJECTION_PHRASES = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "you are now",
    "new instructions",
    "disregard previous",
    "override instructions",
)

_TOPS_TOKENS = (
    "shirt",
    "blouse",
    "top",
    "jacket",
    "hoodie",
    "sweater",
    "tee",
    "t-shirt",
    "cardigan",
    "coat",
    "kurta",
    "kurti",
)
_BOTTOMS_TOKENS = ("trouser", "pant", "jean", "skirt", "short", "legging", "chino", "palazzo")
_ONE_PIECE_TOKENS = (
    "dress",
    "jumpsuit",
    "gown",
    "romper",
    "one-piece",
    "one piece",
    "lehenga",
    "anarkali",
)
_SAREE_TOKENS = ("saree", "sari")


def sanitize_clothing_description(raw: str) -> str:
    """Strip quotes/newlines, cap length (~120), block prompt-injection phrases, fallback if empty."""
    text = (raw or "").replace("\r", " ").replace("\n", " ")
    text = text.replace('"', "").replace("'", "").strip()
    text = re.sub(r"\s+", " ", text)
    lowered = text.lower()
    if not text:
        return _FALLBACK_DESCRIPTION
    if any(phrase in lowered for phrase in _INJECTION_PHRASES):
        return _FALLBACK_DESCRIPTION
    if len(text) > _MAX_DESCRIPTION_LENGTH:
        text = text[:_MAX_DESCRIPTION_LENGTH].rstrip()
    return text


def infer_garment_category(description: str) -> str:
    """Return one of: 'tops' | 'bottoms' | 'one-pieces' | 'saree' | 'other' from the Step 1 phrase."""
    lowered = (description or "").lower()
    if any(token in lowered for token in _SAREE_TOKENS):
        return "saree"
    if any(token in lowered for token in _ONE_PIECE_TOKENS):
        return "one-pieces"
    if any(token in lowered for token in _BOTTOMS_TOKENS):
        return "bottoms"
    if any(token in lowered for token in _TOPS_TOKENS):
        return "tops"
    return "other"


def resolve_garment_category(
    *,
    sku_category: str | None,
    drape_style: str | None,
    description: str,
) -> str:
    """Trust sku_category if valid; else saree if drape_style == 'nivi'; else infer; else 'other'."""
    if sku_category and sku_category in _VALID_CATEGORIES:
        return sku_category
    if (drape_style or "").strip().lower() == "nivi":
        return "saree"
    inferred = infer_garment_category(description)
    if inferred in _VALID_CATEGORIES:
        return inferred
    return "other"


def map_fashn_category(category: str) -> str:
    """Map to FASHN v1.6: 'tops' | 'bottoms' | 'one-pieces'.

    saree -> one-pieces; other -> one-pieces; unknown -> one-pieces.
    """
    if category in _FASHN_CATEGORIES:
        return category
    return "one-pieces"


def compose_tryon_prompt(*, clothing_description: str, garment_category: str) -> str:
    """Build the Step 2 OpenAI Images edit prompt.

    Interpolates ``clothing_description`` and freezes identity, body shape, pose,
    lighting, and background. Not saree-only. Appends Nivi drape only when
    ``garment_category`` is ``saree``.
    """
    description = clothing_description.strip() or _FALLBACK_DESCRIPTION
    prompt = (
        "Create a high-fidelity, photorealistic virtual try-on image. "
        f'Take the person from the first image and dress them in the "{description}" from the second image.\n\n'
        "Crucial Instructions:\n"
        "1. Preserve Person's Identity: The person's original features — including their face, hair, "
        "body shape, skin tone, and pose — must remain completely unchanged and preserved with high fidelity. "
        "Do not slim, fatten, elongate, or restage the body. "
        "Freeze pose, limbs, body proportions, camera angle, and background. "
        "Do not rotate, reframe, or restage the person. Change garments only.\n"
        f'2. Realistic Fit: The "{description}" should be realistically draped and fitted onto the person, '
        "matching the lighting, shadows, and overall style of the original photo of the person. "
        "Replace the current clothes; do not overlay a collage.\n"
        "3. Keep Background: Do not alter the background of the person's image. "
        "The final output should be just the person with the new clothing seamlessly integrated.\n"
        "Keep the SAME person: face, skin tone, hair, pose, body proportions, camera angle, background. "
        "Photoreal fashion photograph. No text, no watermark, no collage, no floating fabric overlay."
    )
    if garment_category == "saree":
        prompt += (
            " Traditional Nivi drape: pallu over the left shoulder, stacked waist pleats, "
            "blouse from the set if visible. Preserve the pallu motif, border, colour, and weave."
        )
    return prompt
