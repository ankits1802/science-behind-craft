from __future__ import annotations

import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.citations import SourceRef
from app.research.craft_page import CraftPage, PageCraft, without_evidence
from app.research.crafts import CraftRef
from app.science.records import ProcessRecords
from app.services.craft_page import craft_page
from app.services.craft_page_records import ClaimFacts, CraftPageRecords, TermRecord
from app.services.curation_keys import curated_id
from app.services.curation_preview import master_craft, preview_records
from app.services.knowledge_view import ClaimView

from ..contracts.golden import golden_json
from .import_support import AJRAKH, AJRAKH_GOLDEN, plan_of, raw

SOURCE_ID = str(uuid.UUID(int=500))
STAGE_CONCEPT = uuid.UUID(int=600)
HISTORY_CONCEPT = uuid.UUID(int=601)
BOILED = "The cloth is boiled in madder to fix the red colour on the alum mordant."
BOILED_AGAIN = "The cloth is boiled in madder to fix a red colour on the alum mordant."
GUESS = "Madder may have reached Kutch through the old trade with Persia by sea."
MOVED = "Ajrakh printers moved from Sindh to Kutch about four hundred years ago."


def ajrakh_records() -> CraftPageRecords:
    craft, names = master_craft(AJRAKH)
    return preview_records(plan_of(AJRAKH), craft, names)


@pytest.fixture(scope="module")
def ajrakh() -> CraftPage:
    return craft_page(ajrakh_records())


def test_the_curated_page_lists_every_claim_once_in_all_evidence(ajrakh: CraftPage) -> None:
    filed = [
        claim_id for entry, _ in ajrakh.evidence.entries() for claim_id in [entry.claim_id, *entry.folded_ids]
    ]
    assert sorted(map(str, filed)) == sorted(str(claim.id) for claim in ajrakh.claims)
    assert len(ajrakh.claims) == 132
    assert {claim.provenance for claim in ajrakh.claims} == {"CURATED"}


def test_hypotheses_stand_apart(ajrakh: CraftPage) -> None:
    guessed = {curated_id(AJRAKH, claim["id"]) for claim in raw(AJRAKH)["claims"] if claim.get("hypothesis")}
    apart = {
        claim_id for entry in ajrakh.evidence.hypotheses for claim_id in [entry.claim_id, *entry.folded_ids]
    }
    assert apart == guessed
    grouped = {
        entry.claim_id for group in ajrakh.evidence.groups for s in group.subjects for entry in s.entries
    }
    assert grouped.isdisjoint(guessed)


def test_the_overview_rests_on_the_dossier(ajrakh: CraftPage) -> None:
    assert ajrakh.curated and ajrakh.curation is not None and ajrakh.curation.version == 1
    assert len(ajrakh.overview.lede) == 3
    assert [section.discipline for section in ajrakh.overview.sections] == [
        section["discipline"] for section in raw(AJRAKH)["overview"]["sections"]
    ]
    assert len(ajrakh.overview.key_facts) == len(raw(AJRAKH)["overview"]["keyFacts"])
    assert {section.basis for section in ajrakh.overview.sections} == {"CURATED"}
    assert any(
        span.term_key == "saaj"
        for section in ajrakh.overview.sections
        for s in section.sentences
        for span in s.terms
    )


def test_places_name_their_district_and_role(ajrakh: CraftPage) -> None:
    ajrakhpur = next(
        place for place in ajrakh.places if place.name == "Ajrakhpur" and place.role == "PRACTISED"
    )
    assert ajrakhpur.district is not None and (ajrakhpur.district.lgd, ajrakhpur.district.name) == (
        449,
        "Kachchh",
    )
    sindh = next(place for place in ajrakh.places if place.name == "Sindh" and place.role == "ORIGIN")
    assert (sindh.country, sindh.district, sindh.state) == ("Pakistan", None, None)
    assert len(ajrakh.sources_differ) == 14


def test_the_process_numbers_only_ordered_stages(ajrakh: CraftPage) -> None:
    stages = ajrakh.process.stages
    assert len(stages) == 14
    assert [stage.order for stage in stages[:11]] == list(range(1, 12))
    assert [stage.order for stage in stages[11:]] == [None, None, None]
    indigo = next(stage for stage in stages if stage.name == "Indigo dyeing")
    assert [timing.text for timing in indigo.timing] == ["10-15 min"]
    assert [reaction.balanced for reaction in indigo.reactions] == [False]


def citation(claim_id: uuid.UUID, level: str) -> dict[str, Any]:
    return {
        "id": f"cite-{claim_id.int}",
        "claimId": str(claim_id),
        "sourceId": SOURCE_ID,
        "quote": "boiled in a madder bath for hours",
        "locator": "p. 4",
        "context": None,
        "evidence": "QUOTED",
        "level": level,
    }


def stored_view(number: int, text: str, concept: uuid.UUID, level: str = "PROVISIONAL") -> ClaimView:
    claim_id = uuid.UUID(int=number)
    return ClaimView(claim_id, text, level, "", concept, citations=[citation(claim_id, level)])


def uncurated_craft() -> tuple[CraftRef, PageCraft]:
    ref = CraftRef(
        slug="Bagru-Hand-Block-Print", name="Bagru Hand Block Print", path="/crafts/Bagru-Hand-Block-Print"
    )
    craft = PageCraft(
        **ref.model_dump(),
        id=uuid.UUID(int=900),
        local_name=None,
        category_name=None,
        sub_category_name=None,
        gi_status=None,
        state_of_practice=["Rajasthan"],
        state_of_origin=[],
    )
    return ref, craft


def uncurated_records() -> CraftPageRecords:
    views = (
        stored_view(1, BOILED, STAGE_CONCEPT),
        stored_view(2, BOILED_AGAIN, STAGE_CONCEPT),
        stored_view(3, GUESS, HISTORY_CONCEPT, level="HYPOTHESIS"),
        stored_view(4, MOVED, HISTORY_CONCEPT),
    )
    stage, history = ("Madder dyeing", "PROCESS_STAGE"), ("Migration", "HISTORICAL_CONTEXT")
    origins = ("IMPORT", "LIVE_RESEARCH", "IMPORT", "IMPORT")
    subjects = (stage, stage, history, history)
    facts = {
        view.id: ClaimFacts(origin, False, None, *subject)
        for view, origin, subject in zip(views, origins, subjects, strict=True)
    }
    ref, craft = uncurated_craft()
    source = SourceRef.model_validate(
        {"id": SOURCE_ID, "kind": "BOOK", "title": "Block printing in Rajasthan", "authors": [], "year": None}
        | dict.fromkeys(("doi", "url", "publisher", "licence", "attribution"))
        | {"reliability": "B"}
    )
    process = ProcessRecords(ref, (), (), (), (), (), {}, {})
    terms = (TermRecord("dabu", "dabu", ("daboo",)),)
    return CraftPageRecords(craft, None, views, facts, {SOURCE_ID: source}, process, terms=terms)


def test_a_craft_without_a_dossier_gets_a_page_from_its_claims() -> None:
    page = craft_page(uncurated_records())
    assert (page.curated, page.curation) == (False, None)
    assert page.overview.lede == [] and page.overview.key_facts == []
    sections = {section.discipline: section for section in page.overview.sections}
    assert set(sections) == {"PROCESS", "HISTORY"}
    assert {section.basis for section in sections.values()} == {"STORED_CLAIMS"}
    assert [sentence.text for sentence in sections["HISTORY"].sentences] == [MOVED]
    assert [term.key for term in page.glossary] == ["dabu"]
    assert page.glossary[0].meaning is None


def test_duplicates_fold_under_one_entry_and_answers_are_told_apart() -> None:
    page = craft_page(uncurated_records())
    (process,) = [group for group in page.evidence.groups if group.discipline == "PROCESS"]
    (entry,) = process.subjects[0].entries
    assert (entry.claim_id, entry.folded_ids) == (uuid.UUID(int=2), [uuid.UUID(int=1)])
    provenance = {claim.id.int: claim.provenance for claim in page.claims}
    assert provenance == {1: "SEED", 2: "FROM_ANSWERS", 3: "SEED", 4: "SEED"}
    assert [entry.claim_id for entry in page.evidence.hypotheses] == [uuid.UUID(int=3)]


def test_a_page_refusing_an_unlisted_claim() -> None:
    page = craft_page(uncurated_records())
    plain = page.model_dump(mode="json", by_alias=True)
    plain["overview"]["sections"][0]["sentences"][0]["claimIds"] = [str(uuid.UUID(int=77))]
    with pytest.raises(ValidationError, match="does not list"):
        CraftPage.model_validate(plain)


STUDENT_CLAIMS = 119
STUDENT_SOURCES = 18


def golden_page() -> CraftPage:
    return CraftPage.model_validate(golden_json(AJRAKH_GOLDEN))


def test_a_reader_without_all_evidence_gets_only_the_claims_the_page_cites() -> None:
    full = golden_page()
    student = without_evidence(full)
    assert student.evidence is None
    assert (len(student.claims), len(student.sources)) == (STUDENT_CLAIMS, STUDENT_SOURCES)
    assert {claim.id for claim in student.claims} == set(full.referenced_claim_ids())
    cited = {citation.source_id for claim in student.claims for citation in claim.citations}
    assert {source.id for source in student.sources} == cited
    kept = student.model_dump(exclude={"evidence", "claims", "sources"})
    assert kept == full.model_dump(exclude={"evidence", "claims", "sources"})


def test_the_researcher_view_is_the_whole_golden() -> None:
    full = golden_page()
    assert full.evidence is not None and len(full.claims) == 132


def test_a_page_without_evidence_refuses_an_uncited_claim() -> None:
    full = golden_page()
    plain = without_evidence(full).model_dump(mode="json", by_alias=True)
    plain["claims"] = full.model_dump(mode="json", by_alias=True)["claims"]
    plain["sources"] = full.model_dump(mode="json", by_alias=True)["sources"]
    with pytest.raises(ValidationError, match="only claims its parts cite"):
        CraftPage.model_validate(plain)
