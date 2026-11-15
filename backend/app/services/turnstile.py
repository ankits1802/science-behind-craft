import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_enabled() -> bool:
    return bool((get_settings().turnstile_secret_key or "").strip())


def site_key() -> str | None:
    if not turnstile_enabled():
        return None
    return (get_settings().turnstile_site_key or "").strip() or None


def required_but_missing() -> bool:
    return get_settings().is_production and site_key() is None


async def verify(token: str | None, remote_ip: str | None) -> bool:
    if not turnstile_enabled():
        return True
    if not token:
        return False
    data = {"secret": get_settings().turnstile_secret_key or "", "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(VERIFY_URL, data=data)
        return bool(response.json().get("success"))
    except httpx.HTTPError, ValueError:
        logger.warning("turnstile verification could not be completed")
        return False
