"""Gateway settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """BFF configuration: downstream URLs and auth mode."""

    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8001
    catalog_base_url: str = "http://127.0.0.1:8002"
    ai_service_base_url: str = "http://127.0.0.1:8003"
    kiosk_device_token: str = "change-me-kiosk-device-token"
    auth_dev_bypass: bool = False
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = GatewaySettings()
