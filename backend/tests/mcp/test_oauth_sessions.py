import uuid
from datetime import UTC, datetime, timedelta

from app.models import OAuthGrant, User
from app.services.oauth_tokens import grant_matches_user, sessions_live_since

ENDED_AT = datetime(2026, 11, 19, 12, tzinfo=UTC)


def account(**changes: object) -> User:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Ravi Shah",
        "email": "ravi@example.org",
        "role": "RESEARCHER",
        "tokenVersion": 3,
        "sessionsValidFrom": ENDED_AT,
        "deletedAt": None,
    }
    values.update(changes)
    return User(**values)


def test_a_code_or_connection_made_before_sessions_were_ended_is_dead() -> None:
    assert not sessions_live_since(account(), ENDED_AT - timedelta(seconds=1))
    assert sessions_live_since(account(), ENDED_AT + timedelta(seconds=1))
    assert not sessions_live_since(account(deletedAt=ENDED_AT), ENDED_AT + timedelta(minutes=1))
    assert not sessions_live_since(None, ENDED_AT)


def test_a_connection_dies_when_the_account_s_token_version_moves() -> None:
    grant = OAuthGrant(userTokenVersion=3, createdAt=ENDED_AT + timedelta(minutes=1))
    assert grant_matches_user(grant, account())
    assert not grant_matches_user(grant, account(tokenVersion=4))
    assert not grant_matches_user(grant, None)
