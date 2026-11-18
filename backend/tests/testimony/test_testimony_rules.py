import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.testimony import CONTRIBUTION_MOVES, Speaker
from app.research.voices import VoiceQuote
from app.services.artisan_voice_builder import Offered, _block, chosen_quotes, voice_quote_payload
from app.services.testimony_readback import kalavigyan_ids, refreshed_document
from app.services.testimony_store import TestimonyQuote as Quote, page_offset
from app.services.testimony_writes import ContributionEdit, _reason_problems

APP = Path(__file__).resolve().parents[2] / "app"
SOURCE = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
LINE = "An artisan of Ajrakh Printing, Kachchh, Gujarat"


def test_the_moves_are_the_contracts_table() -> None:
    assert set(CONTRIBUTION_MOVES) == {
        ("PENDING", "APPROVED"),
        ("PENDING", "REJECTED"),
        ("PENDING", "WITHDRAWN"),
        ("APPROVED", "APPROVED"),
        ("APPROVED", "REJECTED"),
        ("APPROVED", "WITHDRAWN"),
    }


def test_rejected_and_withdrawn_are_final() -> None:
    assert not any(source in {"REJECTED", "WITHDRAWN"} for source, _target in CONTRIBUTION_MOVES)


def test_a_rejection_names_a_known_reason_and_other_needs_a_note() -> None:
    assert _reason_problems("UNCLEAR", None) == []
    assert _reason_problems("OTHER", "  ") == ["a reason of OTHER needs a note"]
    assert _reason_problems("OTHER", "Said by the interviewer, not the artisan.") == []
    assert _reason_problems("WRONG", None)[0].startswith("the reason is one of NOT_ABOUT_THE_CRAFT")
    assert _reason_problems("UNCLEAR", "x" * 501) == ["a note is at most 500 characters"]


def test_an_edit_names_the_fields_it_changed_never_their_text() -> None:
    edit = ContributionEdit(version=3, claim_text="A shorter claim.", english_checked=True)
    assert edit.fields() == ["claimText", "englishSource"]
    assert ContributionEdit(version=1, quote="kapda").fields() == ["quote"]


def test_a_cursor_is_an_offset_of_whole_pages() -> None:
    assert page_offset(None) == 0
    assert page_offset("25") == 25
    for bad in ("7", "-25", "abc", "100025"):
        with pytest.raises(InvalidInput):
            page_offset(bad)


def quote(
    item: str, *, line: str = LINE, english: str = "We wash the cloth", day: int = 1, **extra: Any
) -> Quote:
    return Quote(
        item_id=f"kalavigyan:{item}",
        contribution_id=uuid.uuid4(),
        craft_id=uuid.uuid4(),
        discipline="PROCESS",
        speaker=Speaker(name=None, role="ARTISAN", district="Kachchh", state="Gujarat", line=line),
        quote="हम कपड़े को बहते पानी में धोते हैं",
        language="hi",
        english=english,
        english_source="MACHINE",
        source_id=SOURCE,
        locator="1:05–1:12",
        recorded_on="2026-11",
        approved_at=datetime(2026, 11, day, tzinfo=UTC),
        corroborated_by=extra.get("corroborated_by", ()),
        source={},
    )


def test_corroborated_quotes_come_first_then_the_ones_on_the_sections_words() -> None:
    plain = quote("a", english="Indigo is dipped at dawn", day=9)
    near = quote("b", english="The alum bath fixes the red", day=2, line="Bilal, Ajrakh Printing")
    backed = quote(
        "c",
        english="Unrelated words here",
        day=1,
        line="Zoya, Ajrakh Printing",
        corroborated_by=(uuid.uuid4(),),
    )
    stems = {"alum", "bath", "red"}
    chosen = chosen_quotes(Offered((plain, near, backed)), stems, limit=2)
    assert [q.item_id for q in chosen] == ["kalavigyan:c", "kalavigyan:b"]


def test_distinct_speakers_are_preferred_before_a_second_quote_of_one_speaker() -> None:
    first = quote("a", day=9)
    second = quote("b", day=8)
    other = quote("c", day=1, line="Bilal, Ajrakh Printing")
    chosen = chosen_quotes(Offered((first, second, other)), set(), limit=2)
    assert [q.item_id for q in chosen] == ["kalavigyan:a", "kalavigyan:c"]
    assert len(chosen_quotes(Offered((first, second, other)), set(), limit=3)) == 3


def test_named_and_unnamed_testimony_quotes_are_valid_v2_voice_quotes() -> None:
    credit = Speaker(
        name="Bilal Khatri",
        role="ARTISAN",
        district="Kachchh",
        state="Gujarat",
        line="Bilal Khatri, Ajrakh Printing, Kachchh, Gujarat",
    )
    named = Quote(**{**quote("a").__dict__, "speaker": credit})
    for testimony in (named, quote("b")):
        payload = voice_quote_payload(testimony, {})
        shown = VoiceQuote.model_validate(payload)
        assert (shown.origin, shown.workshop, shown.english_source) == ("KALAVIGYAN", None, "MACHINE")
        assert str(shown.recorded_on) == "2026-11"
        assert shown.speaker.line == testimony.speaker.line
    assert voice_quote_payload(quote("b"), {})["speaker"]["name"] is None


def test_a_quote_the_block_model_refuses_is_dropped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    leaked = Quote(**{**quote("a").__dict__, "quote": "मेरा नंबर 98765 43210 है"})
    with caplog.at_level(logging.WARNING):
        assert _block("s1.voices1", [leaked], {}) is None
    assert "refused by the artisan_voice model" in caplog.text


def document(*quotes: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    block = {"id": "s1.voices1", "kind": "artisan_voice", "version": 2, "quotes": list(quotes), "removed": 0}
    prose = {"id": "s1.b1", "kind": "prose", "sentences": [{"citations": [{"sourceId": "kept-source"}]}]}
    return {"sections": [{"id": "s1", "blocks": [prose, block]}], "sources": sources}


def stored_quote(
    item: str, *, origin: str = "KALAVIGYAN", source: str = "conversation-source"
) -> dict[str, Any]:
    return {
        "itemId": item,
        "origin": origin,
        "sourceId": source,
        "speaker": {"name": "Old Name", "line": "Old Name, Ajrakh"},
    }


def test_read_back_drops_withdrawn_testimony_counts_it_and_refreshes_the_speaker() -> None:
    kept_id, gone_id = uuid.uuid4(), uuid.uuid4()
    stored = document(
        stored_quote(f"kalavigyan:{kept_id}", source=str(SOURCE)),
        stored_quote(f"kalavigyan:{gone_id}", source="gone-source"),
        stored_quote("FIELD_REPOSITORY:m1:s1", origin="FIELD_REPOSITORY", source="portal-source"),
        sources=[
            {"id": "kept-source", "attribution": None},
            {"id": str(SOURCE), "attribution": "Old Name, Ajrakh"},
            {"id": "gone-source", "attribution": "Old Name, Ajrakh"},
            {"id": "portal-source", "attribution": None},
        ],
    )
    assert kalavigyan_ids(stored) == [kept_id, gone_id]
    current = Quote(**{**quote("x").__dict__, "source": {"id": str(SOURCE), "attribution": LINE}})
    shown = refreshed_document(stored, {kept_id: current})
    block = shown["sections"][0]["blocks"][1]
    assert [q["itemId"] for q in block["quotes"]] == [f"kalavigyan:{kept_id}", "FIELD_REPOSITORY:m1:s1"]
    assert block["removed"] == 1
    assert block["quotes"][0]["speaker"] == {
        "name": None,
        "role": "ARTISAN",
        "district": "Kachchh",
        "state": "Gujarat",
        "line": LINE,
    }
    assert [s["id"] for s in shown["sources"]] == ["kept-source", str(SOURCE), "portal-source"]
    assert shown["sources"][1]["attribution"] == LINE


def test_only_the_testimony_store_selects_claims_of_the_artisan_origin() -> None:
    selecting = re.compile(r"Claim\.origin\s*(==|\.in_\(|!=)")
    readers = []
    for path in APP.rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if selecting.search(line) and ("ARTISAN" in line or "testimony" in line.casefold()):
                readers.append(path.name)
    assert readers == ["testimony_store.py"]
