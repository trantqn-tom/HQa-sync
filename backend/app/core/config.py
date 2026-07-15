from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BHQ Sheet Sync"
    env: str = "development"
    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    database_url: str
    secret_key: str
    token_encryption_key: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    google_spreadsheet_id: str
    google_sheet_name: str = "Raw data ebay"
    sync_hour: int = 8
    sync_minute: int = 30
    sync_timezone: str = "Asia/Ho_Chi_Minh"
    auto_clear_after_sync: bool = True
    admin_username: str = "administrator"
    admin_password: str = "HQa12345"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
