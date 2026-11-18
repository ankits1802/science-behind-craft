import json
from datetime import timedelta
from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.research.structured import StructuredReply
from app.schemas.artisan import ArtisanTranscript
from app.voice.artisan_extract import (
    TESTIMONY_SCHEMA,
    TESTIMONY_SYSTEM_PROMPT,
    extract_contributions,
    extraction_message,
    extraction_parts,
    kept_contributions,
)

from .artisan_fakes import (
    CONVERSATION_ID,
    TERMS,
    MemoryArtisanStore,
    artisan_turn as said,
    conversation,
    kalavigyan_turn as asked,
    sealed,
    timed_words,
)
from .fakes import START, FakeModel, cipher

SOAK = "We soak the cloth in camel dung and castor oil for 3 days before printing."
INDIGO = "The indigo vat must stay warm, so we cover it with sacks every night"
NOW = START + timedelta(minutes=12)


def transcript(*, words: bool = False) -> ArtisanTranscript:
    first = said(1, SOAK, words=timed_words(SOAK, 12.0) if words else None)
    return ArtisanTranscript(
        turns=[asked(0, "How do you begin?"), first, asked(2, "What next?"), said(3, INDIGO)]
    )


def item(**changes: Any) -> dict[str, Any]:
    base = {
        "turn": 1,
        "quote": "We soak the cloth in camel dung and castor oil for 3 days",
        "english": "We soak the cloth in camel dung and castor oil for 3 days",
        "claim": "The cloth is soaked in camel dung and castor oil for 3 days before printing.",
        "discipline": "PROCESS",
        "conceptType": "PROCESS_STAGE",
        "conceptName": "Soaking the cloth",
    }
    return base | changes


def kept(*items: dict[str, Any], language: str = "en", words: bool = False) -> list[Any]:
    return kept_contributions({"contributions": list(items)}, transcript(words=words), language, frozenset())


def test_a_quote_copied_from_the_artisan_s_turn_is_kept_as_their_words() -> None:
    [written] = kept(item())
    assert written.quote == "We soak the cloth in camel dung and castor oil for 3 days"
    assert written.english == written.quote and written.english_source == "ORIGINAL"
    assert (written.ordinal, written.precision) == (1, "TURN")
    assert (written.start_ms, written.end_ms) == (10_000, 18_000)


def test_word_timings_place_the_quote_within_its_turn() -> None:
    [written] = kept(
        item(quote="camel dung and castor oil", claim="The cloth is soaked in camel dung and castor oil."),
        words=True,
    )
    assert written.precision == "WORD"
    assert (written.start_ms, written.end_ms) == (14_500, 16_900)


def test_another_language_keeps_the_model_s_english_as_a_machine_translation() -> None:
    [written] = kept(item(english="We soak the cloth in dung and oil for 3 days"), language="gu")
    assert written.english == "We soak the cloth in dung and oil for 3 days"
    assert written.english_source == "MACHINE"


def test_items_that_break_a_rule_are_dropped() -> None:
    broken = [
        item(turn=2),
        item(turn=9),
        item(quote="We soak the cloth in cow dung for 3 days"),
        item(quote="soak the"),
        item(quote="e soak the cloth in camel dung and castor oil"),
        item(claim="The cloth is soaked for 5 days."),
        item(
            english="We soak the cloth for three days",
            quote="soak the cloth in camel dung and castor oil for 3 days",
        ),
        item(discipline="ASTROLOGY"),
        item(conceptType="OPEN_QUESTION"),
        item(conceptName=""),
    ]
    assert kept_contributions({"contributions": broken}, transcript(), "gu", frozenset()) == []
    assert kept_contributions({"contributions": "none"}, transcript(), "en", frozenset()) == []


def test_a_scrubbed_placeholder_is_never_quoted() -> None:
    turns = ArtisanTranscript(
        turns=[
            asked(0, "Who taught you?"),
            said(1, "Call my brother on [number] to learn about the vat.", scrubbed=True),
        ]
    )
    reply = {
        "contributions": [
            item(quote="Call my brother on [number] to learn", english="Call my brother on [number] to learn")
        ]
    }
    assert kept_contributions(reply, turns, "en", frozenset()) == []


def test_a_held_back_name_is_kept_but_screened() -> None:
    text = "Khatri families have printed Ajrakh in this village for nine generations"
    turns = ArtisanTranscript(turns=[asked(0, "Who taught you?"), said(1, text)])
    reply = {
        "contributions": [
            item(quote=text, english=text, claim="Ajrakh has been printed here for nine generations.")
        ]
    }
    [written] = kept_contributions(reply, turns, "en", TERMS)
    assert written.screens == ("NAME_HELD_BACK",)


async def test_extraction_keeps_each_fact_once_and_finishes_done() -> None:
    store = MemoryArtisanStore()
    store.conversations[CONVERSATION_ID] = conversation(transcript=sealed(*transcript().turns), ended_at=NOW)
    overlapping = item(
        quote="castor oil for 3 days before printing", english="castor oil for 3 days before printing"
    )
    second = item(
        turn=3,
        quote=INDIGO,
        english=INDIGO,
        claim="The indigo vat is covered with sacks every night.",
        conceptType="MATERIAL",
        conceptName="Indigo vat",
    )
    model = FakeModel([json.dumps({"contributions": [item(), overlapping, second]})])
    status = await extract_contributions(
        CONVERSATION_ID, artisans=store, model=model, cipher=cipher(), terms=frozenset(), now=NOW
    )
    assert status == "DONE"
    assert [c.ordinal for c in store.contributions] == [1, 3]
    assert model.calls[0]["system"] == TESTIMONY_SYSTEM_PROMPT
    assert model.calls[0]["schema"] == TESTIMONY_SCHEMA


async def test_nothing_drawn_finishes_none() -> None:
    store = MemoryArtisanStore()
    store.conversations[CONVERSATION_ID] = conversation(transcript=sealed(*transcript().turns), ended_at=NOW)
    status = await extract_contributions(
        CONVERSATION_ID,
        artisans=store,
        model=FakeModel(['{"contributions": []}']),
        cipher=cipher(),
        terms=frozenset(),
        now=NOW,
    )
    assert status == "NONE" and store.contributions == []


class Refusing:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    async def __call__(self, **_: Any) -> StructuredReply:
        error = ExternalFailure("no", kind="error")
        error.kind = self.kind
        raise error


@pytest.mark.parametrize(("kind", "expected"), [("ceiling", "WAITING"), ("unavailable", "FAILED")])
async def test_a_spend_refusal_waits_and_a_provider_failure_fails(kind: str, expected: str) -> None:
    store = MemoryArtisanStore()
    store.conversations[CONVERSATION_ID] = conversation(transcript=sealed(*transcript().turns), ended_at=NOW)
    status = await extract_contributions(
        CONVERSATION_ID, artisans=store, model=Refusing(kind), cipher=cipher(), terms=frozenset(), now=NOW
    )
    assert status == expected and store.conversations[CONVERSATION_ID].extraction == expected


async def test_a_conversation_already_extracted_is_not_claimed_again() -> None:
    store = MemoryArtisanStore()
    store.conversations[CONVERSATION_ID] = conversation(
        transcript=sealed(*transcript().turns), extraction="DONE"
    )
    model = FakeModel([])
    assert (
        await extract_contributions(
            CONVERSATION_ID, artisans=store, model=model, cipher=cipher(), terms=frozenset(), now=NOW
        )
        is None
    )
    assert model.calls == []


def test_long_conversations_are_read_in_whole_turns_and_at_most_three_calls() -> None:
    long = "x" * 3_900
    turns = [said(i, long) for i in range(1, 36)]
    parts = extraction_parts(ArtisanTranscript(turns=[asked(0, "Begin"), *turns]))
    assert [len(part) for part in parts] == [10, 10, 10]
    assert parts[1][0].ordinal == 11


def test_the_message_gives_each_artisan_turn_after_kalavigyan_s_question() -> None:
    message = extraction_message(conversation(), transcript(), transcript().turns[1:2])
    assert message.index('ref="k0"') < message.index('ref="t1"')
    assert SOAK in message
