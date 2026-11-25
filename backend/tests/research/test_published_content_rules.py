import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.published_edits import (
    FactEdit,
    FieldChange,
    PictureEdit,
    StagedEdit,
    edited_fields,
    fact_text_problems,
    field_changes,
    moved_fields,
    shown_value,
)
from app.research.staged_reviews import STAGED_KIND_ACTIONS, ConfirmedItem, StagedDecision, stored_decision

ITEM = uuid.UUID("6f1c2a4e-8d3b-4c5a-9e7f-0a1b2c3d4e41")
WHY = "The page shows another craft's picture."
QUOTE = "Lime keeps the indigo vat alkaline, so the dye stays reduced"


def decision(**changes: Any) -> dict[str, Any]:
    return {"kind": "IMAGES", "id": str(ITEM), "action": "remove", "reason": WHY} | changes


def edit(**fields: Any) -> dict[str, Any]:
    return decision(action="edit", edit={"fields": fields})


def test_every_kind_an_admin_reviews_takes_removal_or_edit_beside_its_queue_actions() -> None:
    assert dict(STAGED_KIND_ACTIONS) == {
        "FACTS": ("approve", "reject", "raise", "retract", "edit"),
        "COMPONENTS": ("approve", "reject", "remove", "edit"),
        "LAYOUTS": ("approve", "reject", "remove"),
        "STRUCTURE": ("approve", "reject", "remove", "edit"),
        "READINGS": ("approve", "reject", "remove"),
        "LAYERS": ("approve", "reject", "remove"),
        "STAGES": ("approve", "reject", "remove"),
        "PICTURE_CHECKS": ("approve", "reject"),
        "SOURCES": ("correct", "remove"),
        "SOURCES_DIFFER": ("clear",),
        "IMAGES": ("remove", "edit"),
    }


@pytest.mark.parametrize(
    ("refused", "says"),
    [
        (decision(action="approve"), "A IMAGES item is remove or edit, not approve."),
        (decision(action="edit"), "An edit names the fields it changes as edit"),
        (decision(edit={"fields": {"caption": "A vat"}}), "An edit names the fields it changes as edit"),
        (decision(craft="Kutch-Ajrakh"), "Only a component's removal names the one page"),
        (decision(entry="NATIVE_NAME"), "Only a removal or an edit of a structure entry"),
        (decision(kind="SOURCES", source={"title": "Indigo vats"}), "Only a source correction carries"),
        (
            decision(kind="FACTS"),
            "A FACTS item is approve or reject or raise or retract or edit, not remove.",
        ),
        (decision(kind="STRUCTURE", action="approve", entry="CONFLICT"), "Only a removal or an edit"),
    ],
)
def test_a_staged_removal_or_edit_takes_only_what_its_kind_allows(refused: dict[str, Any], says: str) -> None:
    with pytest.raises(ValidationError, match=says):
        StagedDecision.model_validate(refused)


def test_a_structure_entry_names_its_kind_and_a_component_its_one_page() -> None:
    entry = StagedDecision.model_validate(decision(kind="STRUCTURE", entry="NATIVE_NAME"))
    page = StagedDecision.model_validate(decision(kind="COMPONENTS", craft="Bagh-Print"))
    source = StagedDecision.model_validate(decision(kind="SOURCES"))
    assert (entry.entry, page.craft, source.source) == ("NATIVE_NAME", "Bagh-Print", None)


def test_a_person_changes_an_edit_s_reason_but_never_its_values_or_its_action() -> None:
    proposed = StagedDecision.model_validate(edit(caption="A clay vat of indigo"))
    reasoned = proposed.changed_to(
        ConfirmedItem.model_validate(
            {"id": str(uuid.uuid4()), "action": "edit", "reason": "The caption misnames the vat."}
        )
    )
    assert (reasoned.kind, reasoned.id, reasoned.reason) == ("IMAGES", ITEM, "The caption misnames the vat.")
    assert reasoned.edit == proposed.edit
    removal = ConfirmedItem.model_validate({"id": str(ITEM), "action": "remove", "reason": WHY})
    with pytest.raises(InvalidInput, match="An edit is confirmed as it was staged"):
        proposed.changed_to(removal)
    staged_removal = StagedDecision.model_validate(decision())
    with pytest.raises(InvalidInput, match="An edit is confirmed as it was staged"):
        staged_removal.changed_to(
            ConfirmedItem.model_validate({"id": str(ITEM), "action": "edit", "reason": WHY})
        )


def test_a_stored_edit_keeps_a_field_it_empties() -> None:
    staged = StagedDecision.model_validate(
        decision(action="edit", edit={"fields": {"focal": None}, "before": {"focal": {"x": 0.1}}})
    )
    assert stored_decision(staged) == {
        "action": "edit",
        "reason": WHY,
        "kind": "IMAGES",
        "id": str(ITEM),
        "edit": {"fields": {"focal": None}, "before": {"focal": {"x": 0.1}}},
    }
    assert StagedDecision.model_validate(stored_decision(staged)) == staged


def test_an_edit_keeps_only_the_fields_it_names_in_their_canonical_names() -> None:
    assert edited_fields(PictureEdit, {"altText": "A clay vat", "focal": None}) == {
        "alt_text": "A clay vat",
        "focal": None,
    }
    place = edited_fields(PictureEdit, {"place": {"slot": "MASTHEAD"}})
    assert place == {"place": {"stage_id": None, "material_id": None, "slot": "MASTHEAD", "task_key": None}}
    with pytest.raises(ValidationError, match="caption cannot be emptied"):
        edited_fields(PictureEdit, {"caption": None})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        edited_fields(PictureEdit, {"licence": "CC-BY-4.0"})
    with pytest.raises(ValidationError, match="a focal box lies inside its picture"):
        edited_fields(PictureEdit, {"focal": {"x": 0.6, "y": 0.1, "width": 0.5, "height": 0.2}})
    with pytest.raises(ValidationError, match="personal data"):
        edited_fields(FactEdit, {"text": "Write to dyer@example.org for the vat's recipe."})


def test_an_edit_is_stale_when_a_field_it_changes_moved_since_it_was_staged() -> None:
    assert moved_fields({"text": "now", "caption": "kept"}, {"text": "then", "caption": "kept"}) == ["text"]
    assert moved_fields({"focal": {"x": 0.1, "y": 0.2}}, {"focal": {"y": 0.2, "x": 0.1}}) == []


def test_a_new_fact_text_is_matched_against_its_quotes() -> None:
    assert fact_text_problems("Lime keeps the vat alkaline so the indigo stays reduced.", [QUOTE]) == []
    assert fact_text_problems("Lime keeps the vat alkaline.", []) == [
        "This fact has no quote to match a new text against: retract it and propose the new text with its "
        "quotes."
    ]
    assert fact_text_problems("Dyers wash the cloth in the river at dawn.", [QUOTE]) == [
        "The new text says too little of what its quotes say: 0% of its words are in them, and an edit keeps "
        "at least 50%."
    ]
    (figures,) = fact_text_problems("Lime keeps the vat alkaline for 12 days.", [QUOTE])
    assert figures.startswith("12") and figures.endswith(
        "in the new text appears in none of the fact's quotes."
    )


def test_the_batch_shows_each_changed_field_before_and_after() -> None:
    staged = StagedEdit(
        fields={"alt_text": "A clay vat of indigo", "colours": ["red", "black"], "focal": None},
        before={"alt_text": "A vat", "colours": ["red"], "focal": {"y": 0.2, "x": 0.1}},
    )
    assert field_changes(staged) == [
        FieldChange(field="Alt text", before="A vat", after="A clay vat of indigo"),
        FieldChange(field="Colours", before="red", after="red, black"),
        FieldChange(field="Focal", before='{"x": 0.1, "y": 0.2}', after=None),
    ]
    long = shown_value("word " * 100)
    assert long is not None and len(long) == 300 and long.endswith("…")
