import asyncio
import json
from collections.abc import Sequence
from typing import Any

import pytest

from app.research.blocks import ProseBlock
from app.research.crafts import CraftResolution
from app.research.image_relevance import ClaimText
from app.services.answering import AnswerAsk

from ..composer.fixtures import QUESTION
from ..images.fakes import FakeMediaStore, FakeSource, candidate
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH
from .fakes import (
    ALUM_CLAIM_ID,
    GLOSSARY,
    MORDANT_BATH,
    SOURCES,
    VIEWS,
    WRITTEN_LAKE_ID,
    WRITTEN_WASH_ID,
    FakeEnrichment,
    FakeStore,
    enriched,
    pipeline,
    streamed,
    translation,
)
from .piece_fakes import MemoryPieces
from .test_answer_flow import REPLY, detailed, events

ENGLISH_SPANS = [
    [("Alum", "alum"), ("alizarin", "alizarin"), ("cotton", "cotton")],
    [("alum", "alum")],
    [],
]
ALUM_HI = "फिटकरी वह मॉर्डेंट है जो alizarin को cotton से बाँधती है।"
LAKE_HI = "मॉर्डेंट के घोल में 8 g/L फिटकरी थी और उसे 60 °C तक गरम किया गया।"
WASH_HI = "लाल लेक 20 धुलाइयों तक टिकी रही।"


class BrokenMedia(FakeMediaStore):
    async def claim_texts(self, claim_ids: Sequence[Any]) -> list[ClaimText]:
        raise ConnectionError("the media store went away")


def block_events(found: list[tuple[str, dict]]) -> list[dict[str, Any]]:
    return [payload["block"] for name, payload in found if name == "block"]


def spans_of(block: dict[str, Any]) -> list[list[tuple[str, str]]]:
    return [[(span["text"], span["termKey"]) for span in s["terms"]] for s in block["sentences"]]


def memory() -> MemoryPieces:
    return MemoryPieces(views=list(VIEWS), sources=dict(SOURCES))


def hindi_model() -> FakeModel:
    def reply(**texts: str) -> str:
        items = [{"key": key, "text": text} for key, text in texts.items()]
        return json.dumps({"items": items}, ensure_ascii=False)

    return FakeModel(
        [
            reply(s1="रसायन"),
            reply(**{"s1.b1.1": ALUM_HI, "s1.b1.2": LAKE_HI, "s1.b1.3": WASH_HI}),
            reply(**{"s1.open.1": "धोने के पानी में चूना लाल रंग को चमका सकता है।"}),
            reply(**{"follow-up:0": "कच्छ अजरख के लिए फिटकरी का घोल कैसे तैयार किया जाता है?"}),
        ]
    )


def prose(text: str) -> ProseBlock:
    sentence = {"id": "s1.b1.1", "text": text, "level": "REVIEWED", "citations": VIEWS[0].citations}
    return ProseBlock.model_validate(
        {
            "id": "s1.b1",
            "kind": "prose",
            "version": 1,
            "reuse": None,
            "sentences": [{**sentence, "terms": []}],
        }
    )


async def test_a_section_with_cited_claims_streams_one_picture_after_its_prose() -> None:
    enrichment = enriched()
    store = FakeStore()
    found = events(await streamed(detailed(), pipeline(replies=[REPLY], store=store, enrichment=enrichment)))
    names = [(name, payload.get("block", {}).get("kind")) for name, payload in found]
    prose_at, images_at = names.index(("block", "prose")), names.index(("block", "images"))
    assert prose_at < images_at < names.index(("section_done", None))
    prose_block, images = block_events(found)
    assert images["id"] == "s1.b2"
    assert [item["media"]["display"] for item in images["items"]] == ["INLINE"]
    cited = {c["claimId"] for sentence in prose_block["sentences"] for c in sentence["citations"]}
    assert {claim for item in images["items"] for claim in item["claimIds"]} <= cited
    (ask,) = enrichment.asks
    assert (ask.block_id, ask.craft_name) == ("s1.b2", "Kutch Ajrakh")
    assert ask.claim_ids == (ALUM_CLAIM_ID, WRITTEN_LAKE_ID, WRITTEN_WASH_ID)
    assert dict(found)["section_done"] == {"sectionId": "s1", "state": "READY", "searched": None}
    (finished,) = store.finished
    assert [block.kind for block in finished["explainer"].sections[0].blocks] == ["prose", "images"]


def failing_source() -> FakeEnrichment:
    return FakeEnrichment(sources=[FakeSource("openverse", [MORDANT_BATH], failing=True)])


def slow_source() -> FakeEnrichment:
    return FakeEnrichment(sources=[FakeSource("searxng", [MORDANT_BATH], hanging=True)], search_seconds=0.01)


def slow_pictures() -> FakeEnrichment:
    return FakeEnrichment(sources=[FakeSource("searxng", [MORDANT_BATH], hanging=True)], wait_seconds=0.01)


def no_relevant_picture() -> FakeEnrichment:
    unrelated = candidate("commons", 3, "Mountain lake at dawn", licence="CC0", author="A")
    return FakeEnrichment(sources=[FakeSource("wikimedia_commons", [unrelated])])


def broken_store() -> FakeEnrichment:
    return FakeEnrichment(sources=[FakeSource("wikimedia_commons", [MORDANT_BATH])], media=BrokenMedia({}))


@pytest.mark.parametrize(
    "enrichment", [failing_source, slow_source, slow_pictures, no_relevant_picture, broken_store]
)
async def test_pictures_that_fail_or_come_late_leave_the_section_ready_without_them(enrichment: Any) -> None:
    store = FakeStore()
    found = events(
        await streamed(detailed(), pipeline(replies=[REPLY], store=store, enrichment=enrichment()))
    )
    assert [block["kind"] for block in block_events(found)] == ["prose"]
    assert dict(found)["section_done"] == {"sectionId": "s1", "state": "READY", "searched": None}
    assert "error" not in dict(found)
    (finished,) = store.finished
    assert [block.kind for block in finished["explainer"].sections[0].blocks] == ["prose"]


async def test_english_sentences_carry_their_glossary_terms_and_the_stored_piece_keeps_them() -> None:
    pieces = memory()
    found = events(
        await streamed(
            detailed(), pipeline(replies=[REPLY], pieces=pieces, enrichment=FakeEnrichment(entries=GLOSSARY))
        )
    )
    (prose_block,) = block_events(found)
    assert spans_of(prose_block) == ENGLISH_SPANS
    (stored,) = pieces.current()
    assert stored.kind == "prose"
    assert [
        [(s.text, s.term_key) for s in sentence.terms] for sentence in stored.payload.sentences
    ] == ENGLISH_SPANS


async def test_pictures_are_shown_but_never_stored_as_pieces() -> None:
    pieces = memory()
    await streamed(detailed(), pipeline(replies=[REPLY], pieces=pieces, enrichment=enriched()))
    ((_, _, sections),) = pieces.kept
    assert [[block.kind for block in section.blocks] for section in sections] == [["prose"]]
    assert [piece.kind for piece in pieces.current()] == ["prose"]


async def test_a_term_named_twice_in_a_sentence_is_marked_once_where_it_first_appears() -> None:
    enrichment = await FakeEnrichment(entries=GLOSSARY).tools().for_answer(AJRAKH)
    (sentence,) = enrichment.marked(prose("Alum water is alum dissolved in water.")).sentences
    assert [(span.text, span.term_key) for span in sentence.terms] == [("Alum", "alum")]


async def test_a_translated_sentence_keeps_only_the_spans_its_text_still_shows() -> None:
    pieces = memory()
    ask = AnswerAsk(question=QUESTION, depth="DETAILED", language="hi")
    answer_pipeline = pipeline(
        replies=[REPLY],
        pieces=pieces,
        translated=translation(hindi_model()),
        enrichment=FakeEnrichment(entries=GLOSSARY),
    )
    (shown,) = block_events(events(await streamed(ask, answer_pipeline)))
    assert [s["text"] for s in shown["sentences"]] == [ALUM_HI, LAKE_HI, WASH_HI]
    assert spans_of(shown) == [[("alizarin", "alizarin"), ("cotton", "cotton")], [], []]
    (stored,) = pieces.current()
    assert [
        [(s.text, s.term_key) for s in sentence.terms] for sentence in stored.payload.sentences
    ] == ENGLISH_SPANS


async def test_a_reused_section_gets_pictures_from_its_claims_and_no_templated_follow_ups() -> None:
    pieces = memory()
    await streamed(
        detailed(), pipeline(replies=[REPLY], pieces=pieces, enrichment=FakeEnrichment(entries=GLOSSARY))
    )
    enrichment = enriched()
    found = events(await streamed(detailed(), pipeline(pieces=pieces, enrichment=enrichment)))
    reused, images = block_events(found)
    assert (reused["id"], reused["reuse"] is not None, spans_of(reused)) == ("s1.b1", True, ENGLISH_SPANS)
    assert (images["id"], images["kind"], images["reuse"]) == ("s1.b2", "images", None)
    (ask,) = enrichment.asks
    assert ask.claim_ids == (ALUM_CLAIM_ID, WRITTEN_LAKE_ID, WRITTEN_WASH_ID)
    assert dict(found)["section_done"] == {"sectionId": "s1", "state": "READY", "searched": None}
    assert dict(found)["follow_ups"]["items"] == []


async def test_a_glossary_that_cannot_be_read_leaves_sentences_unmarked() -> None:
    enrichment = FakeEnrichment(entries=GLOSSARY, glossary_failure=ConnectionError("the database went away"))
    found = events(await streamed(detailed(), pipeline(replies=[REPLY], enrichment=enrichment)))
    (prose_block,) = block_events(found)
    assert spans_of(prose_block) == [[], [], []]
    assert enrichment.crafts == [AJRAKH.slug]


async def test_an_answer_for_any_craft_reads_no_glossary_and_searches_pictures_by_claim_words() -> None:
    none = CraftResolution(status="NONE", craft=None, candidates=[], normalised="why", script="Latn")
    enrichment = enriched()
    found = events(
        await streamed(detailed(), pipeline(resolution=none, replies=[REPLY], enrichment=enrichment))
    )
    assert enrichment.crafts == []
    assert [ask.craft_name for ask in enrichment.asks] == [None]
    assert [block["kind"] for block in block_events(found)] == ["prose", "images"]
    assert spans_of(block_events(found)[0]) == [[], [], []]


async def test_pictures_still_searching_when_a_section_stops_are_cancelled() -> None:
    hanging = FakeEnrichment(sources=[FakeSource("searxng", [MORDANT_BATH], hanging=True)])
    enrichment = await hanging.tools().for_answer(AJRAKH)
    before = asyncio.all_tasks()
    with pytest.raises(LookupError):
        async with enrichment.searching() as pictures:
            pictures.start("s1", [prose("Alum is the mordant that binds alizarin to cotton.")])
            await asyncio.sleep(0)
            running = asyncio.all_tasks() - before
            raise LookupError("the section stopped")
    assert running
    assert all(task.cancelled() for task in running)
