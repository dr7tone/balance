"""Настройки приложения. Значения берутся из переменных окружения (файл .env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BALANCE"
    api_prefix: str = "/api"

    database_url: str = "sqlite:///./balance.db"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440

    redis_url: str = ""          # пусто — кэш Redis не используется
    cors_origins: str = "*"      # список источников через запятую или "*"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["*"]


settings = Settings()
