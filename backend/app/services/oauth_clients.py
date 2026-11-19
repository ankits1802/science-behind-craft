from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OAuthClient
from app.research.oauth_contract import (
    GRANT_TYPES,
    RESPONSE_TYPES,
    ClientRegistration,
    RegisteredClient,
    registered_client,
)
from app.research.oauth_metadata import PUBLIC_CLIENT_AUTH

__all__ = ["find_client", "register_client"]


async def register_client(
    session: AsyncSession, registration: ClientRegistration, *, now: datetime
) -> RegisteredClient:
    row = OAuthClient(**registered_client(registration), createdAt=now)
    session.add(row)
    await session.flush()
    return RegisteredClient(
        client_id=str(row.id),
        client_id_issued_at=int(now.timestamp()),
        client_name=row.name,
        redirect_uris=list(row.redirectUris),
        grant_types=list(GRANT_TYPES),
        response_types=list(RESPONSE_TYPES),
        token_endpoint_auth_method=PUBLIC_CLIENT_AUTH,
        client_uri=row.clientUri,
    )


async def find_client(session: AsyncSession, client_id: str | None) -> OAuthClient | None:
    if not client_id:
        return None
    try:
        key = uuid.UUID(client_id)
    except ValueError:
        return None
    return await session.get(OAuthClient, key)
