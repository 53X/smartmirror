"""Choose FASHN, OpenAI image-edit, optional stub, or fail closed."""

from app.settings import settings
from app.tryon.fal_fashn import FalFashnVendor
from app.tryon.http_vendor import HttpTryOnVendor
from app.tryon.interface import TryOnVendor
from app.tryon.openai_tryon import OpenAITryOnVendor
from app.tryon.stub import StubTryOnVendor
from app.tryon.unconfigured import UnconfiguredTryOnVendor


def get_tryon_vendor() -> TryOnVendor:
    """Prefer a real drape model. Never default to overlay."""
    if settings.fal_key:
        return FalFashnVendor()
    if settings.tryon_vendor_url and settings.tryon_vendor_api_key:
        return HttpTryOnVendor()
    if settings.openai_api_key:
        return OpenAITryOnVendor()
    if settings.tryon_allow_stub:
        return StubTryOnVendor()
    return UnconfiguredTryOnVendor()
