import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.api import reading_deps
from app.models import User


def reader(role: str) -> User:
    return User(id=uuid.UUID(int=11), name="Asha", email="asha@example.org", role=role)


def stored(profile: Any, monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    asked: list[uuid.UUID] = []

    async def student_profile(_session: Any, user_id: uuid.UUID) -> Any:
        asked.append(user_id)
        return profile

    async def released(_session: Any) -> None:
        return None

    monkeypatch.setattr(reading_deps.reader_profiles, "student_profile", student_profile)
    monkeypatch.setattr(reading_deps, "release_connection", released)
    return asked


async def test_a_student_without_a_profile_is_refused_with_no_guessed_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored(None, monkeypatch)
    with pytest.raises(HTTPException) as refused:
        await reading_deps.asker_style(reader("STUDENT"), None)
    assert refused.value.status_code == 409
    assert refused.value.detail == "Finish setting up your profile first."
    assert refused.value.headers == {"X-Profile-Required": "student"}


async def test_the_style_comes_from_the_stored_band(monkeypatch: pytest.MonkeyPatch) -> None:
    stored(SimpleNamespace(ageBand="14_17", gender="UNSAID"), monkeypatch)
    assert await reading_deps.asker_style(reader("STUDENT"), None) == "TEEN"


async def test_other_roles_read_no_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = stored(None, monkeypatch)
    assert await reading_deps.asker_style(reader("ARTISAN"), None) is None
    assert asked == []
