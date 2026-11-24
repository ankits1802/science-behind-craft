from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["BROWSER_PATH", "RENDERER_PORT", "RendererSettings"]

BROWSER_PATH = "/opt/chrome-headless-shell/current/chrome-headless-shell"
RENDERER_PORT = 8091


class RendererSettings(BaseSettings):
    host: str = Field(default="127.0.0.1", alias="RENDERER_HOST")
    port: int = Field(default=RENDERER_PORT, ge=1, le=65535, alias="RENDERER_PORT")
    browser: str = Field(default=BROWSER_PATH, alias="RENDERER_BROWSER")
    site: str = Field(default="http://localhost:3000", alias="PUBLIC_WEB_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=None, populate_by_name=True, extra="ignore")
