from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_picture_files
from app.models import User
from app.research.upload_links import (
    SEVERAL_FILES_LIFETIME,
    UPLOAD_LINK_LIFETIME,
    SlotCraft,
    SlotDeclaration,
    UploadSlot,
    slot_lifetime,
)
from app.services import upload_links

from .modern_client import result_of
from .test_mcp_file_uploads import FACT, LINK_ID, PHOTO, WORDS, file_call, photographs, sending
from .test_mcp_studio_tools import API, Endpoints
from .test_upload_links import FakeSession, person, shown, slot

SECOND_PHOTO = {**PHOTO, "id": "photo-2", "name": "vat.jpg"}
NOW = datetime(2026, 11, 26, 9, tzinfo=UTC)


def lifetimes(monkeypatch: pytest.MonkeyPatch) -> list[timedelta]:
    given: list[timedelta] = []

    async def start(
        session: Any,
        user: User,
        target: UploadSlot,
        declaration: SlotDeclaration | None,
        *,
        now: datetime,
        lifetime: timedelta = UPLOAD_LINK_LIFETIME,
    ) -> upload_links.IssuedLink:
        given.append(lifetime)
        return upload_links.IssuedLink(
            link_token="kvup_pg_link-token",
            slot_token="kvup_sl_slot-token",
            expires_at=now + lifetime,
            craft=SlotCraft(slug="Kutch-Ajrakh", name="Kutch Ajrakh"),
            stage=None,
            facts=[],
            link_id=LINK_ID,
        )

    monkeypatch.setattr(upload_links, "start_upload", start)
    monkeypatch.setattr(mcp_picture_files, "endpoints_or_none", lambda: Endpoints(API))
    return given


def test_a_single_file_keeps_half_an_hour_and_several_files_get_seventy_five_minutes() -> None:
    assert slot_lifetime(1) == UPLOAD_LINK_LIFETIME == timedelta(minutes=30)
    assert slot_lifetime(2) == slot_lifetime(10) == SEVERAL_FILES_LIFETIME == timedelta(minutes=75)


async def test_a_slot_opened_with_a_longer_lifetime_expires_at_its_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shown(monkeypatch, {FACT: "Alum binds alizarin to cotton."})
    session = FakeSession(answers=[0])
    issued = await upload_links.start_upload(
        session,  # type: ignore[arg-type]
        person(),
        slot(),
        None,
        now=NOW,
        lifetime=SEVERAL_FILES_LIFETIME,
    )
    (row,) = session.added
    assert row.expiresAt == issued.expires_at == NOW + timedelta(minutes=75)


async def test_two_photographs_sent_together_each_get_a_seventy_five_minute_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    given = lifetimes(monkeypatch)
    picture = {"upload": True, "claim_ids": [str(FACT)], **WORDS}
    arguments = photographs(pictures=[picture, picture], files=[PHOTO, SECOND_PHOTO])
    first = await result_of(file_call("give_pictures", arguments), sending())
    assert first["resultType"] == "upload_required"
    assert given == [SEVERAL_FILES_LIFETIME, SEVERAL_FILES_LIFETIME]
    assert [target["fileId"] for target in first["uploads"]] == ["photo-1", "photo-2"]


async def test_one_photograph_keeps_today_s_half_hour_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    given = lifetimes(monkeypatch)
    first = await result_of(file_call("give_pictures", photographs()), sending())
    assert first["resultType"] == "upload_required"
    assert given == [UPLOAD_LINK_LIFETIME]
