"""Refuse to pretend overlay is try-on when no vendor is configured."""

from app.tryon.interface import TryOnRequest, TryOnResult, TryOnVendor


class UnconfiguredTryOnVendor(TryOnVendor):
    """Fails loudly so the kiosk never shows a pasted collage as a 'look'."""

    @property
    def name(self) -> str:
        return "unconfigured"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        """Raise until OPENAI_API_KEY or FAL_KEY is set."""
        raise RuntimeError(
            "Virtual try-on is not configured. Set OPENAI_API_KEY (gpt-image-1) or "
            "FAL_KEY (FASHN v1.6). Overlay compositing is disabled."
        )
