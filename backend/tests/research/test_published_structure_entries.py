import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.structure_edits import EDITS, UNEDITED, StageAfterEdit
from app.services.curated_index import IndexAfter, IndexNativeName, IndexTerm
from app.services.published_kinds import Editable
from app.services.published_structure_entries import (
    checked_item,
    edited_page,
    entries_of,
    page_entries,
    without_entry,
)
from app.services.structure_proposals_page import target_problem

from ..structure.pages import HELD_A, HELD_B, HELD_C, MATERIAL_CONCEPT, OLD_AFTER, curated_page, key, stage

TERM_CLAIM = key("term-claim")


def glossary() -> IndexTerm:
    return IndexTerm(
        key="W01",
        term_key="ajrakh-resist",
        term="Resist",
        names=["Resist"],
        meaning="A paste that keeps the dye off the cloth where it is printed.",
        language=None,
        script=None,
        concept_id=MATERIAL_CONCEPT,
        claim_ids=[TERM_CLAIM],
    )


def test_a_page_lists_each_structure_entry_with_the_fact_it_rests_on() -> None:
    entries = page_entries(curated_page(glossary=[glossary()]))
    assert [(entry.kind, entry.key, entry.name, entry.claim_ids) for entry in entries] == [
        ("STAGE_AFTER", "P02", "Stage P02's colour after: Pale", (OLD_AFTER,)),
        ("NATIVE_NAME", "Ajrakh", "Native name: Ajrakh (hi)", (HELD_A,)),
        ("GLOSSARY_TERM", "W01", "Glossary term: Resist", (TERM_CLAIM,)),
        ("CONFLICT", "When the river dried", "Conflict: When the river dried", (HELD_B, HELD_C)),
    ]
    assert [entry.kind for entry in entries_of(curated_page(), HELD_C)] == ["CONFLICT"]
    assert entries_of(curated_page(), HELD_C, "NATIVE_NAME") == []


def test_a_removed_entry_leaves_its_page_and_every_other_entry_stays() -> None:
    page = curated_page(glossary=[glossary()])
    (after,) = entries_of(page, OLD_AFTER)
    (term,) = entries_of(page, TERM_CLAIM)
    (conflict,) = entries_of(page, HELD_B)
    assert [held.after for held in without_entry(page, after).stages] == [None, None]
    assert without_entry(page, term).glossary == [] and term.term_key == "ajrakh-resist"
    kept = without_entry(page, conflict)
    assert kept.conflicts == [] and kept.native_names == page.native_names and kept.stages == page.stages


def test_an_edit_changes_only_the_fields_it_names_and_passes_the_entry_s_own_rules() -> None:
    page = curated_page()
    (after,) = entries_of(page, OLD_AFTER)
    changed = edited_page(page, after, {"text": "Deep red", "colours": ["RED"]})
    assert changed.stages[1].after == IndexAfter(text="Deep red", colours=["RED"], claim_id=OLD_AFTER)
    assert changed.stages[0] == page.stages[0] and changed.native_names == page.native_names
    with pytest.raises(ValidationError, match="each colour is named once"):
        checked_item(after, {"colours": ["RED", "RED"]})
    second = IndexNativeName(text="Ajrak", language="hi", script=None, claim_id=HELD_C)
    two = curated_page(native_names=[*page.native_names, second])
    (named,) = entries_of(two, HELD_C, "NATIVE_NAME")
    clash = checked_item(named, {"text": "Ajrakh"})
    assert (
        target_problem(without_entry(two, named), clash)
        == "the page already gives the native name Ajrakh in hi"
    )
    assert target_problem(without_entry(two, named), checked_item(named, {"text": "Ajarakh"})) is None


def test_a_stage_s_why_and_a_reaction_are_removed_not_edited() -> None:
    page = curated_page(stages=[stage("P01", key("s"), key("c"), why_claim_id=HELD_A)])
    why = next(entry for entry in entries_of(page, HELD_A) if entry.kind == "STAGE_WHY")
    refused = Editable(why.current, EDITS.get(why.kind), UNEDITED.get(why.kind))
    with pytest.raises(InvalidInput, match="A stage's why is the fact it rests on"):
        refused.fields_of({"text": "Washed twice"})
    assert set(EDITS) == {
        "STAGE_AFTER",
        "NATIVE_NAME",
        "BOTANICAL_NAME",
        "GLOSSARY_TERM",
        "CONFLICT",
        "OPEN_QUESTION",
        "GI_RECORD",
    }
    assert EDITS["STAGE_AFTER"] is StageAfterEdit and set(UNEDITED) == {"STAGE_WHY", "REACTION"}
