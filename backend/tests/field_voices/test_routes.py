import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from app.api.routes import field_voices
from app.core.errors import InvalidInput
from app.main import app
from app.research.voices import VoiceQuote, VoiceSpeaker
from app.services.field_voices_reading import list_offset


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_a_full_transcript_is_read_without_signing_in(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def withdrawn(_session: Any, _recording_id: uuid.UUID) -> None:
        return None

    monkeypatch.setattr(field_voices, "field_transcript", withdrawn)
    response = await client.get(f"/api/field-voices/recordings/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_the_show_all_list_knows_only_quotes_and_images(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/crafts/Kutch-Ajrakh/field-voices", params={"kind": "transcripts"})
    assert response.status_code == 422


@pytest.mark.parametrize("cursor", ["-25", "abc", "26", "100025", "2.5"])
def test_a_cursor_the_list_did_not_issue_is_refused(cursor: str) -> None:
    with pytest.raises(InvalidInput, match="Unknown cursor"):
        list_offset(cursor)


def test_list_cursors_are_page_offsets() -> None:
    assert [list_offset(None), list_offset("25"), list_offset("100000")] == [0, 25, 100_000]


def quote(**speaker: object) -> VoiceQuote:
    return VoiceQuote.model_validate(
        {
            "itemId": "kalavigyan:9b3b6f0e-0000-4000-8000-000000000003",
            "origin": "KALAVIGYAN",
            "speaker": {"role": "ARTISAN", "line": "An artisan of Ajrakh Print of Kutch, Kachchh, Gujarat"}
            | speaker,
            "quote": "We wash the cloth in the river twice before the first print.",
            "language": "gu",
            "english": "We wash the cloth twice before printing.",
            "englishSource": "REVIEWED",
            "sourceId": "9b3b6f0e-0000-4000-8000-000000000004",
            "locator": "2:10–2:31",
            "recordedOn": "2026-11",
        }
    )


def test_a_speaker_without_a_name_is_credited_by_the_line() -> None:
    shown = quote()
    assert (shown.speaker.name, shown.speaker.line) == (
        None,
        "An artisan of Ajrakh Print of Kutch, Kachchh, Gujarat",
    )
    assert shown.recorded_on == "2026-11"
    assert quote(name="Asha Demo").speaker.name == "Asha Demo"
    assert set(VoiceSpeaker.model_fields) == {"name", "line", "role", "years_in_craft", "district", "state"}


def test_a_quote_never_carries_a_phone_number() -> None:
    with pytest.raises(ValueError, match="phone"):
        quote(line="Call 98250 12345")
