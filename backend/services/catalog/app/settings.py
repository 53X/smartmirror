"""Catalog settings loaded from environment."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class CatalogSettings(BaseSettings):
    """Runtime configuration for the catalog microservice."""

    catalog_host: str = "0.0.0.0"
    catalog_port: int = 8002
    catalog_data_dir: Path = _BACKEND_ROOT / "data" / "catalog"
    public_media_base_url: str = "http://127.0.0.1:8002"
    log_level: str = "INFO"
    catalog_seed_demo: bool = True
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = CatalogSettings()
