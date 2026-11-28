import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.mcp_page_arguments import DraftAdd, bundle_parts
from app.research.page_drafts import (
    DraftAddition,
    DraftParts,
    part_summaries,
    parts_counts,
    with_added,
    without,
)
from app.research.page_proposal_parts import proposal_parts
from app.research.page_proposals import PageBundle, PartReport
from app.research.section_proposals import SECTION_CLAIMS_PER_SENTENCE_MAX, SectionPart

ALUM = uuid.UUID("5ec70000-0000-4000-8000-0000000000a1")
MADDER = uuid.UUID("5ec70000-0000-4000-8000-0000000000a2")
SUBJECT = {"kind": "craft", "slug": "Kutch-Ajrakh"}
PROPOSAL = uuid.UUID("5ec70000-0000-4000-8000-0000000000b1")


def section(field: str = "CHEMISTRY", *texts: str) -> dict[str, Any]:
    written = texts or ("Alum is printed before the madder bath.", "Madder gives a red colour on cotton.")
    ids = [str(ALUM), str(MADDER)]
    return {
        "field": field,
        "sentences": [{"text": text, "claim_ids": [ids[n % 2]]} for n, text in enumerate(written)],
    }


def test_a_section_is_its_field_and_sentences_in_order_each_resting_on_the_facts_it_names() -> None:
    found = SectionPart.model_validate(section())
    assert found.sentences[0].text == "Alum is printed before the madder bath."
    assert found.claim_ids() == [ALUM, MADDER]
    assert found.sentences[0].model_dump(mode="json") == {
        "text": "Alum is printed before the madder bath.",
        "claimIds": [str(ALUM)],
    }


@pytest.mark.parametrize(
    "sentence",
    [
        {"text": "Madder gives a red colour.", "claim_ids": []},
        {"text": "Madder gives a red colour.", "claim_ids": [str(MADDER), str(MADDER)]},
        {"text": "Madder gives a red colour.", "claim_ids": [str(uuid.uuid4()) for _ in range(9)]},
        {"text": "", "claim_ids": [str(MADDER)]},
    ],
)
def test_a_sentence_citing_no_fact_a_fact_twice_too_many_facts_or_nothing_is_refused(sentence: dict) -> None:
    assert SECTION_CLAIMS_PER_SENTENCE_MAX == 8
    with pytest.raises(ValidationError):
        SectionPart.model_validate({"field": "CHEMISTRY", "sentences": [sentence]})


def test_a_bundle_holds_a_section_alone_and_writes_each_field_once() -> None:
    alone = PageBundle.model_validate({"subject": SUBJECT, "sections": [section()]})
    assert [part.field for part in alone.sections] == ["CHEMISTRY"]
    assert bundle_parts(alone) == 1
    with pytest.raises(ValidationError, match="writes each field's section once"):
        PageBundle.model_validate({"subject": SUBJECT, "sections": [section(), section()]})
    assert alone.model_dump(mode="json")["sections"][0]["sentences"][0]["claimIds"] == [str(ALUM)]


def test_a_bundle_without_sections_dumps_as_it_did_before_them() -> None:
    bundle = PageBundle.model_validate({"subject": SUBJECT, "layout": {"baseVersion": 0, "entries": []}})
    assert "sections" not in bundle.model_dump(mode="json")


def test_a_draft_s_later_section_for_a_field_replaces_its_earlier_one_and_is_removed_by_index() -> None:
    held = with_added(DraftParts(), DraftAddition.model_validate({"sections": [section()]}))
    again = with_added(
        held, DraftAddition.model_validate({"sections": [section("CHEMISTRY", "Alum is printed.")]})
    )
    assert [part.sentences[0].text for part in again.sections] == ["Alum is printed."]
    both = with_added(again, DraftAddition.model_validate({"sections": [section("HISTORY")]}))
    assert [part.field for part in both.sections] == ["CHEMISTRY", "HISTORY"]
    assert parts_counts(both).sections == 2
    assert [line.summary for line in part_summaries(both) if line.part == "section"] == [
        "CHEMISTRY section, 1 sentence: Alum is printed.",
        "HISTORY section, 2 sentences: Alum is printed before the madder bath.",
    ]
    assert [part.field for part in without(both, "section", 0).sections] == ["HISTORY"]
    with pytest.raises(ValueError, match="no section 5"):
        without(both, "section", 5)


def test_an_edit_draft_add_takes_sections_in_the_shape_a_draft_holds() -> None:
    added = DraftAdd.model_validate({"sections": [section()]})
    assert added.holds()
    assert DraftAddition.model_validate(added.model_dump(exclude_none=True)).sections[0].field == "CHEMISTRY"


def test_an_accepted_section_joins_the_page_proposal_in_the_sections_queue_under_its_chapter() -> None:
    bundle = PageBundle.model_validate({"subject": SUBJECT, "sections": [section()]})
    report = PartReport(
        part="section", index=0, outcome="ACCEPTED", status="PENDING", id=str(PROPOSAL), message="m"
    )
    parts = proposal_parts(bundle, [report], None)
    assert [(part.part, part.kind, part.id, part.chapter) for part in parts] == [
        ("section", "SECTIONS", PROPOSAL, "chem")
    ]
    assert parts[0].title == "The chemistry section, 2 sentences: Alum is printed before the madder bath."
    refused = report.model_copy(update={"outcome": "REFUSED"})
    assert proposal_parts(bundle, [refused], None) == []
