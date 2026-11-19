import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OAuthClient, OAuthCode, OAuthGrant, User
from app.services.upkeep_clients import abandoned_client_count, remove_abandoned_clients

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

DAY = timedelta(days=1)
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
RESOURCE = "https://api.kalavigyan.example/api/mcp"
CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        yield opened


def registered(name: str, created: datetime) -> OAuthClient:
    return OAuthClient(id=uuid.uuid4(), name=name, redirectUris=[REDIRECT], createdAt=created)


async def signed_in(session: AsyncSession, connected: OAuthClient, coded: OAuthClient, now: datetime) -> None:
    person = User(
        id=uuid.uuid4(),
        name="Connected Person",
        email=f"{uuid.uuid4().hex[:10]}@example.org",
        role="RESEARCHER",
    )
    session.add(person)
    await session.flush()
    grant = OAuthGrant(
        clientId=connected.id,
        userId=person.id,
        scopes=["read"],
        resource=RESOURCE,
        userTokenVersion=0,
        expiresAt=now + 30 * DAY,
    )
    code = OAuthCode(
        codeHash=uuid.uuid4().hex * 2,
        clientId=coded.id,
        userId=person.id,
        redirectUri=REDIRECT,
        codeChallenge=CHALLENGE,
        scopes=["read"],
        resource=RESOURCE,
        expiresAt=coded.createdAt + timedelta(minutes=5),
    )
    session.add_all([grant, code])
    await session.flush()


async def test_a_client_that_never_signed_anyone_in_for_thirty_days_is_removed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    abandoned = registered("Abandoned", now - 31 * DAY)
    coded = registered("Asked once, never exchanged", now - 40 * DAY)
    connected = registered("Connected", now - 90 * DAY)
    recent = registered("Registered yesterday", now - DAY)
    session.add_all([abandoned, coded, connected, recent])
    await session.flush()
    await signed_in(session, connected, coded, now)
    assert await abandoned_client_count(session, now=now) == 2
    report = await remove_abandoned_clients(session, now=now)
    assert report.as_dict() == {"abandonedRemoved": 2}
    mine = [abandoned.id, coded.id, connected.id, recent.id]
    left = set(await session.scalars(select(OAuthClient.id).where(OAuthClient.id.in_(mine))))
    assert left == {connected.id, recent.id}
    assert await abandoned_client_count(session, now=now) == 0
