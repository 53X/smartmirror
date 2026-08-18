"""Vendor-agnostic Stage B try-on interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TryOnRequest:
    """Inputs for a hosted or stub try-on call. Do not log these image bytes.

    ``face_box`` is (x, y, w, h) in the preprocessed customer still, used for
    the OpenAI identity-lock mask. Other vendors ignore it.
    """

    customer_still: bytes
    reconstructed_sari: bytes
    sku_id: str
    session_id: str
    face_box: tuple[int, int, int, int] | None = None
    clothing_description: str = ""
    garment_category: str = "other"  # Catalog/try-on category; FASHN maps saree → one-pieces.


@dataclass(frozen=True)
class TryOnResult:
    """Successful try-on still plus which vendor produced it."""

    image_png: bytes
    vendor_name: str


class TryOnVendor(ABC):
    """Swap stub vs commercial HTTP vendor without changing job orchestration."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable vendor identifier for job records."""

    @abstractmethod
    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Return a PNG still of the reconstructed sari on the customer."""
