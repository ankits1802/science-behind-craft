import hashlib
import uuid

from app.composer.candidates import compose_request
from app.composer.composer import ModelComposer
from app.research.composition import ComposedAnswer, ComposedSection, ComposedSentence, QuotedSpan
from app.research.evidence import Quote
from app.research.write_back import ClaimWriteBack
from app.services.write_back_plan import INFERRED_REASON, QUOTED_REASON, write_back_plan

from ..composer.fixtures import (
    ALUM_CLAIM_ID,
    GUESS_CLAIM_ID,
    PLAN,
    QUESTION,
    STORED,
    answer,
    pack,
    quote,
    sentence,
)
from ..planner.fakes import FakeModel

ANSWER_ID = uuid.UUID("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9")
ABSTRACT_ID = "crossref:10.1000/lake"
PAGE_ID = "searxng:https://crafts.example.org/ajrakh"
FIGURE_QUOTE = "Mordanting baths of 8 g/L alum were heated to 60 °C"
FIGURE_TEXT = "Mordant baths held 8 g/L alum and were heated to 60 °C."
WASH_QUOTE = "the lake withstood 20 washes"


def composed(
    *sentences: ComposedSentence, open_questions: tuple[ComposedSentence, ...] = ()
) -> ComposedAnswer:
    sections = [ComposedSection(heading="Mordant", sentences=list(sentences))] if sentences else []
    return ComposedAnswer(sections=sections, open_questions=list(open_questions))


def cited(text: str, *spans: tuple[str, str], claims: tuple[uuid.UUID, ...] = ()) -> ComposedSentence:
    evidence = list(dict.fromkeys(ref for ref, _ in spans if ":" in ref))
    return ComposedSentence(
        text=text,
        claim_ids=list(claims),
        evidence_ids=evidence,
        spans=[QuotedSpan(ref=ref, text=span) for ref, span in spans],
    )


def expected_key(text: str) -> str:
    parts = ["claim-write-back/v1", "Kutch-Ajrakh", "MATERIAL", "alum", "states", text]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def test_a_quoted_sentence_becomes_a_provisional_claim_on_its_facet() -> None:
    plan = write_back_plan(
        pack(),
        composed(cited(FIGURE_TEXT, (ABSTRACT_ID, FIGURE_QUOTE))),
        found_by="ANSWER",
        answer_id=ANSWER_ID,
    )
    assert plan.skipped == ()
    (claim,) = plan.claims
    assert (claim.label, claim.evidence_level, claim.level_reason) == ("QUOTED", "PROVISIONAL", QUOTED_REASON)
    assert (claim.subject.concept_type, claim.subject.concept_name) == ("MATERIAL", "alum")
    assert (claim.craft_slug, claim.predicate, claim.found_by, claim.answer_id) == (
        "Kutch-Ajrakh",
        "states",
        "ANSWER",
        ANSWER_ID,
    )
    (citation,) = claim.citations
    assert citation.quote == Quote(text=FIGURE_QUOTE)
    assert (citation.quote_check, citation.relation) == ("PASS", "DIRECT")
    assert citation.evidence.quotes == [Quote(text=FIGURE_QUOTE)]
    assert claim.dedupe_key == expected_key("mordant baths held 8 g/l alum and were heated to 60 °c")


def test_a_reader_quote_keeps_its_locator_and_is_not_added_twice() -> None:
    plan = write_back_plan(
        pack(),
        composed(cited("Ajrakh red survived 20 washes.", (PAGE_ID, WASH_QUOTE))),
        found_by="BACKGROUND",
        answer_id=None,
    )
    (claim,) = plan.claims
    (citation,) = claim.citations
    assert len(citation.evidence.quotes) == 2
    assert citation.quote in citation.evidence.quotes
    assert (claim.found_by, claim.answer_id) == ("BACKGROUND", None)


def test_sentences_on_stored_claims_only_are_not_written_again() -> None:
    stored = cited(
        "Alum binds alizarin.",
        (str(ALUM_CLAIM_ID), "Alum is the mordant that binds"),
        claims=(ALUM_CLAIM_ID,),
    )
    plan = write_back_plan(pack(), composed(stored), found_by="ANSWER", answer_id=ANSWER_ID)
    assert plan.claims == ()
    assert [(s.text, s.reason) for s in plan.skipped] == [
        ("Alum binds alizarin.", "cites stored claims only")
    ]


def test_an_open_question_is_written_as_a_model_inference() -> None:
    guess = cited(
        "Washing may matter as much as the mordant.",
        (str(GUESS_CLAIM_ID), "Lime in the wash water may brighten the red"),
        (PAGE_ID, "fastness rose with mordant strength"),
        claims=(GUESS_CLAIM_ID,),
    )
    plan = write_back_plan(pack(), composed(open_questions=(guess,)), found_by="ANSWER", answer_id=ANSWER_ID)
    (claim,) = plan.claims
    assert (claim.label, claim.evidence_level, claim.level_reason) == (
        "INFERRED",
        "HYPOTHESIS",
        INFERRED_REASON,
    )
    assert [c.relation for c in claim.citations] == ["CONTEXTUAL"]
    assert [c.evidence.id for c in claim.citations] == [PAGE_ID]


def test_a_cited_source_without_a_passing_span_is_a_contextual_citation() -> None:
    sentence_ = ComposedSentence(
        text="Ajrakh uses alum.",
        evidence_ids=[ABSTRACT_ID, PAGE_ID],
        spans=[
            QuotedSpan(ref=ABSTRACT_ID, text="red lake with aluminium ions"),
            QuotedSpan(ref=PAGE_ID, text="this phrase is not in the page"),
        ],
    )
    (claim,) = write_back_plan(pack(), composed(sentence_), found_by="ANSWER", answer_id=ANSWER_ID).claims
    assert claim.label == "QUOTED"
    assert [(c.evidence.id, c.quote_check, c.relation) for c in claim.citations] == [
        (ABSTRACT_ID, "PASS", "DIRECT"),
        (PAGE_ID, "NA", "CONTEXTUAL"),
    ]


def test_a_figure_without_a_passing_quote_is_skipped_with_the_reason() -> None:
    unquoted = cited("The bath was heated to 90 °C.", (ABSTRACT_ID, "red lake with aluminium ions"))
    plan = write_back_plan(pack(), composed(unquoted), found_by="ANSWER", answer_id=ANSWER_ID)
    assert plan.claims == ()
    (skipped,) = plan.skipped
    assert skipped.reason.startswith("breaks the write-back contract")
    assert "90" in skipped.reason


def test_the_same_claim_twice_is_one_write_back_with_both_citations() -> None:
    first = cited("Alizarin forms a red lake.", (ABSTRACT_ID, "Alizarin forms an insoluble red lake"))
    second = cited("alizarin forms a  red lake", (PAGE_ID, WASH_QUOTE))
    (claim,) = write_back_plan(pack(), composed(first, second), found_by="ANSWER", answer_id=ANSWER_ID).claims
    assert [c.evidence.id for c in claim.citations] == [ABSTRACT_ID, PAGE_ID]


async def test_composer_output_feeds_the_write_back_contract() -> None:
    reply = answer(
        (
            "Mordant",
            [
                sentence(FIGURE_TEXT, quote(ABSTRACT_ID, FIGURE_QUOTE)),
                sentence(
                    "Alum binds alizarin.",
                    quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
                ),
            ],
        )
    )
    result = await ModelComposer(model=FakeModel([reply])).compose(compose_request(pack(), QUESTION))
    plan = write_back_plan(pack(), result, found_by="ANSWER", answer_id=ANSWER_ID)
    (claim,) = plan.claims
    assert ClaimWriteBack.model_validate(claim.model_dump()) == claim
    assert claim.passing_quotes == [FIGURE_QUOTE]


def test_research_for_any_craft_writes_claims_that_name_no_craft() -> None:
    any_craft = pack(
        plan=PLAN.model_copy(update={"craft": None}),
        stored=STORED.model_copy(update={"craft_slug": None}),
    )
    plan = write_back_plan(
        any_craft,
        composed(cited(FIGURE_TEXT, (ABSTRACT_ID, FIGURE_QUOTE))),
        found_by="ANSWER",
        answer_id=ANSWER_ID,
    )
    (claim,) = plan.claims
    assert claim.craft_slug is None
    parts = ["claim-write-back/v1", "", "MATERIAL", "alum", "states", FIGURE_TEXT.casefold().rstrip(" .")]
    assert claim.dedupe_key == hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
