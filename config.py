import logging
from functools import lru_cache
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """HR Bot configuration from environment variables"""

    # Database
    database_url: str

    # Telegram
    telegram_token: str
    telegram_webhook_url: str = "https://api.telegram.org"

    # Outlook / Microsoft Graph
    outlook_tenant_id: str
    outlook_client_id: str
    outlook_client_secret: str
    outlook_redirect_uri: str = "http://localhost:8000/auth/outlook/callback"
    outlook_graph_url: str = "https://graph.microsoft.com/v1.0"

    # Timezone
    timezone: str = "Asia/Jerusalem"

    # App
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton"""
    return Settings()
