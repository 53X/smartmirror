"""Runtime configuration for Stage A reconstruct and Stage B try-on."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class AiSettings(BaseSettings):
    """Runtime configuration for Stage A reconstruct and Stage B try-on."""

    ai_host: str = "0.0.0.0"
    ai_port: int = 8003
    ai_data_dir: Path = _BACKEND_ROOT / "data" / "ai"
    log_level: str = "INFO"
    tryon_vendor_url: str = ""
    tryon_vendor_api_key: str = ""
    tryon_vendor_timeout_seconds: int = 180
    fal_key: str = ""
    openai_api_key: str = ""
    openai_tryon_model: str = "gpt-image-1"
    tryon_allow_stub: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = AiSettings()
