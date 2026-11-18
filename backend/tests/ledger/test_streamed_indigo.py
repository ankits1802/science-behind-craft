from collections.abc import Sequence
from typing import Any

import pytest

from app.research.blocks import BlockBase
from app.research.explainer import Block, ExplainerSection
from app.services.claim_ledger import admission_batches
from app.services.explainer_events import ExplainerStream
from app.services.source_merge import source_keys

from .indigo_answer import recorded_sections
from .indigo_blocks import INDIGO_CID
from .indigo_claims import KHAMIR_ART, KHAMIR_PART, SOURCES, Claim, sentence
from .shown import repeated_sentences, restated

REFS = {ref["id"]: ref for ref in SOURCES}


class Recorded:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    async def __call__(self, name: str, data: Any) -> None:
        self.events.append((name, data))

    def blocks(self) -> list[BlockBase]:
        return [data["block"] for name, data in self.events if name == "block"]

    def sources(self) -> list[dict[str, Any]]:
        return [data for name, data in self.events if name == "source"]


async def streamed(order: Sequence[str]) -> Recorded:
    recorded = Recorded()
    stream = ExplainerStream(recorded, language="en")
    sections = {payload["id"]: ExplainerSection.model_validate(payload) for payload in recorded_sections()}
    for section_id in order:
        for batch in admission_batches(sections[section_id].blocks):
            await stream.blocks(section_id, batch, REFS)
    return recorded


def test_blocks_are_admitted_in_the_calls_a_live_section_makes() -> None:
    (chemistry,) = [ExplainerSection.model_validate(p) for p in recorded_sections() if p["id"] == "s1"]
    assert [[block.id for block in batch] for batch in admission_batches(chemistry.blocks)] == [
        ["s1.b1"],
        ["s1.b3", "s1.b4", "s1.b5", "s1.b6", "s1.b7"],
        ["s1.b8"],
    ]


@pytest.mark.parametrize("order", [("s1", "s2", "s3", "s4", "s5"), ("s3", "s5", "s1", "s4", "s2")])
async def test_a_streamed_answer_shows_each_sentence_once_whatever_order_its_sections_finish(
    order: tuple[str, ...],
) -> None:
    shown = (await streamed(order)).blocks()
    assert repeated_sentences(shown) == 0
    assert restated(shown) == []
    indigo = sorted(block.kind for block in shown if getattr(block, "pubchem_cid", None) == INDIGO_CID)
    assert indigo == ["material_card", "molecule_3d"]


async def test_a_streamed_source_is_sent_once_and_before_the_block_that_cites_it() -> None:
    recorded = await streamed(("s1", "s2", "s3", "s4", "s5"))
    sent: set[str] = set()
    for name, data in recorded.events:
        if name == "source":
            sent.add(data["id"])
        else:
            assert set(data["block"].cited_source_ids()) <= sent
    keys = [key for ref in recorded.sources() for key in source_keys(ref)]
    assert len(keys) == len(set(keys))
    assert sum("Journal No. 188" in ref["title"] for ref in recorded.sources()) == 1


async def test_an_open_question_cites_the_source_its_twin_was_merged_into() -> None:
    recorded = Recorded()
    stream = ExplainerStream(recorded, language="en")
    (history,) = [payload for payload in recorded_sections() if payload["id"] == "s5"]
    prose = ExplainerSection.model_validate(history).blocks[0]
    await stream.blocks("s5", [prose], REFS)
    guess = Claim("guess", "Khatris may first have printed ajrakh in Khavda.", (KHAMIR_ART,))
    await stream.open_questions([sentence("s5.open.1", guess.text, guess)], REFS)
    (opened,) = [data["sentence"] for name, data in recorded.events if name == "open_question"]
    assert opened["citations"][0]["sourceId"] == KHAMIR_PART["id"]
    assert KHAMIR_ART["id"] not in {ref["id"] for ref in recorded.sources()}


async def test_only_the_blocks_the_ledger_lets_through_are_translated() -> None:
    translated: list[str] = []

    async def in_language(block: Block) -> Block:
        translated.append(block.id)
        return block

    stream = ExplainerStream(Recorded(), language="hi")
    (chemistry,) = [ExplainerSection.model_validate(p) for p in recorded_sections() if p["id"] == "s1"]
    prose, *_ = chemistry.blocks
    await stream.blocks("s1", [prose], REFS, in_language=in_language)
    again = prose.model_copy(update={"id": "s2.b1"})
    shown = await stream.blocks("s2", [again], REFS, in_language=in_language)
    assert (shown, translated) == ([], ["s1.b1"])
