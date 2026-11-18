import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.guardian_hold import (
    GUARDIAN_CONSENT_REQUIRED_DETAIL,
    GUARDIAN_CONSENT_REQUIRED_HEADER,
    refuse_until_guardian_consent,
)


class Session:
    def __init__(self, held: bool) -> None:
        self.held = held
        self.asked = 0
        self.committed = 0

    async def scalar(self, statement: Any) -> Any:
        self.asked += 1
        return uuid.uuid4() if self.held else None

    async def commit(self) -> None:
        self.committed += 1


def person(role: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role)


@pytest.mark.parametrize(
    "route",
    [
        ("GET", "/api/auth/me"),
        ("GET", "/api/me"),
        ("GET", "/api/privacy/notice"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/profile/me"),
        ("PUT", "/api/profile/me/student"),
    ],
)
async def test_a_held_student_still_reaches_the_routes_that_explain_the_hold(route: tuple[str, str]) -> None:
    session = Session(held=True)
    await refuse_until_guardian_consent(session, person("STUDENT"), route)
    assert session.asked == 0


@pytest.mark.parametrize(
    "route",
    [
        ("POST", "/api/answers/stream"),
        ("GET", "/api/usage/me"),
        ("DELETE", "/api/profile/me/recording-consent"),
        ("GET", "/api/profile/meals"),
        ("POST", "/api/auth/consent"),
    ],
)
async def test_a_held_student_is_refused_everything_else(route: tuple[str, str]) -> None:
    session = Session(held=True)
    with pytest.raises(HTTPException) as refused:
        await refuse_until_guardian_consent(session, person("STUDENT"), route)
    assert refused.value.status_code == 403
    assert refused.value.detail == GUARDIAN_CONSENT_REQUIRED_DETAIL
    assert refused.value.headers == {GUARDIAN_CONSENT_REQUIRED_HEADER: "1"}
    assert session.committed == 1


async def test_a_student_without_the_hold_passes_and_releases_the_connection() -> None:
    session = Session(held=False)
    await refuse_until_guardian_consent(session, person("STUDENT"), ("POST", "/api/answers/stream"))
    assert (session.asked, session.committed) == (1, 1)


@pytest.mark.parametrize("role", ["ARTISAN", "RESEARCHER", "PROFESSOR", "ADMIN", "MASTER_ADMIN"])
async def test_no_other_role_is_ever_asked(role: str) -> None:
    session = Session(held=True)
    await refuse_until_guardian_consent(session, person(role), ("POST", "/api/answers/stream"))
    assert session.asked == 0
