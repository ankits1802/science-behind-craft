import uuid

import pytest

from app.research.planning import ResearchShare, split_share
from app.research.sections import section_specs
from app.science.ladder import process_ladder
from app.services.answer_events import cited_claims
from app.services.answer_translation import translated_block
from app.services.research_ledger import ResearchLedger
from app.services.section_blocks import BlockRefused, KeptSentence, prose_block, prose_problems

from ..planner.fakes import FakeModel
from ..science.golden_process import KUT, RED, golden_records, stage_id
from .fakes import ALUM_CLAIM_ID, SOURCES, VIEWS, WRITTEN_LAKE_ID, translation
from .test_translation_flow import reply

CITED = cited_claims(list(VIEWS), SOURCES)


def kept(text: str, *claims: uuid.UUID) -> KeptSentence:
    return KeptSentence(text, claims, (), False)


def test_a_prose_block_carries_each_sentence_with_its_stored_citations() -> None:
    block = prose_block("s1.b1", [kept("Alum is the mordant.", ALUM_CLAIM_ID)], CITED)
    (sentence,) = block.sentences
    assert (sentence.id, sentence.level, sentence.terms) == ("s1.b1.1", "REVIEWED", [])
    assert [c.id for c in sentence.citations] == ["c0000000-0000-4000-8000-000000000001"]


def test_a_block_with_an_uncited_sentence_is_refused_whole() -> None:
    sentences = [kept("Alum is the mordant.", ALUM_CLAIM_ID), kept("Alum came from Gujarat.")]
    with pytest.raises(BlockRefused) as refused:
        prose_block("s1.b1", sentences, CITED)
    assert refused.value.problems == ("sentence 2 cites no stored claim",)


def test_a_figure_no_cited_claim_or_quote_holds_refuses_the_block() -> None:
    sentences = [kept("Mordant baths held 9 g/L alum.", WRITTEN_LAKE_ID)]
    assert prose_problems(sentences, CITED) == ["sentence 1 states 9, which no cited claim or quote holds"]


async def test_translating_a_ladder_changes_its_sentences_only_and_keeps_their_citations() -> None:
    records = golden_records()
    ladder = process_ladder(records, block_id="s1.b1", stage_ids=[stage_id(KUT), stage_id(RED)])
    payload = ladder.model_dump(mode="json", by_alias=True, exclude_unset=True)
    texts = {claim_id: claim.text for claim_id, claim in records.claims.items()}
    model = FakeModel(
        [reply(**{"s1.b1.1": "काट से काली छपाई होती है।", "s1.b1.2": "लाल रंगाई तांबे के बर्तन में होती है।"})]
    )
    shown = await translated_block(payload, language="hi", translation=translation(model), claim_texts=texts)
    before = [s for stage in payload["stages"] for s in stage["sentences"]]
    after = [s for stage in shown["stages"] for s in stage["sentences"]]
    assert [s["text"] for s in after] == ["काट से काली छपाई होती है।", "लाल रंगाई तांबे के बर्तन में होती है।"]
    assert [s["original"] for s in after] == [s["text"] for s in before]
    assert [s["citations"] for s in after] == [s["citations"] for s in before]
    assert [stage["name"] for stage in shown["stages"]] == [stage["name"] for stage in payload["stages"]]
    assert [stage["conditions"] for stage in shown["stages"]] == [
        stage["conditions"] for stage in payload["stages"]
    ]


def test_sections_follow_the_fields_most_important_first_within_the_depth() -> None:
    fields = ["PROCESS", "CHEMISTRY", "PROCESS", "HISTORY", "CLIMATE", "ECOLOGY", "DESIGN"]
    basic = section_specs(fields, "BASIC")
    assert [(s.id, s.discipline, s.title, s.order) for s in basic] == [
        ("s1", "PROCESS", "How it is made", 1),
        ("s2", "CHEMISTRY", "The chemistry", 2),
        ("s3", "HISTORY", "History", 3),
        ("s4", "CLIMATE", "Climate", 4),
    ]
    assert [(s.discipline, s.title) for s in section_specs([], "EXPERT")] == [("OVERVIEW", "What it is")]


def test_a_research_budget_splits_with_the_remainder_to_the_first_sections() -> None:
    total = ResearchShare(queries=8, native_queries=3, fetches=20)
    shares = [(s.queries, s.native_queries, s.fetches) for s in split_share(total, 3)]
    assert shares == [(3, 1, 7), (3, 1, 7), (2, 1, 6)]


def test_the_ledger_hands_out_no_more_than_the_depth_budget() -> None:
    ledger = ResearchLedger(ResearchShare(queries=2, native_queries=0, fetches=5), 3)
    first = ledger.take(ResearchShare(queries=2, native_queries=0, fetches=5))
    assert (first.queries, first.fetches) == (2, 5)
    assert ledger.take_fresh(ResearchShare(queries=0, native_queries=0, fetches=0)) is None
    ledger.give_back(ResearchShare(queries=1, native_queries=0, fetches=3))
    fresh = ledger.take_fresh(ResearchShare(queries=0, native_queries=0, fetches=0))
    assert fresh is not None and (fresh.queries, fresh.fetches) == (1, 2)
    assert (ledger.left.queries, ledger.left.fetches) == (0, 1)
