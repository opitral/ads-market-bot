from typing import Set

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    api_base_url: str
    bot_token: SecretStr
    database_url: str
    admin_telegram_ids: Set[int]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Settings()
