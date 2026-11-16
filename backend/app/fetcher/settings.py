from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["FetcherSettings"]


class FetcherSettings(BaseSettings):
    host: str = Field(default="127.0.0.1", alias="FETCHER_HOST")
    port: int = Field(default=8090, ge=1, le=65535, alias="FETCHER_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=None, populate_by_name=True, extra="ignore")
