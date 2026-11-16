from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services import managed_secrets
from app.sources.web.brave import BRAVE_KEY_NAME
from app.sources.web.registry import WebSearchConfig

__all__ = ["web_search_config"]


async def web_search_config(session: AsyncSession) -> WebSearchConfig:
    return WebSearchConfig(
        searxng_url=get_settings().searxng_url,
        brave_api_key=await managed_secrets.get_secret(session, BRAVE_KEY_NAME),
    )
