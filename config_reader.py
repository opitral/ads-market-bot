from typing import Set

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    API_BASE_URL: str
    BOT_API_TOKEN: SecretStr
    DATABASE_URL: str
    ADMIN_TELEGRAM_IDS: Set[int]
    DEFAULT_CLIENT_MESSAGE: str
    PAGE_LIMIT: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Settings()
