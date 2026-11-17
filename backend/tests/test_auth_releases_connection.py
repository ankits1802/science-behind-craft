import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import get_current_user_any_step
from app.core.security import create_access_token


class SignedInUser:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.tokenVersion = 0
        self.deletedAt = None
        self.sessionsValidFrom = None


class RecordingSession:
    def __init__(self, user: SignedInUser | None) -> None:
        self.user = user
        self.calls: list[str] = []

    async def get(self, _model: object, _key: object) -> SignedInUser | None:
        self.calls.append("get")
        return self.user

    async def commit(self) -> None:
        self.calls.append("commit")


def bearer(user_id: uuid.UUID) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token(str(user_id), token_version=0)
    )


async def test_signing_in_hands_the_connection_back_before_the_route_runs() -> None:
    user = SignedInUser()
    session = RecordingSession(user)
    found = await get_current_user_any_step(bearer(user.id), session)
    assert found is user
    assert session.calls == ["get", "commit"]


async def test_a_refused_token_never_commits() -> None:
    session = RecordingSession(None)
    with pytest.raises(HTTPException):
        await get_current_user_any_step(bearer(uuid.uuid4()), session)
    assert session.calls == ["get"]
