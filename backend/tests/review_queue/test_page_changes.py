import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.monograph_document import MonographDocument
from app.research.page_changes import page_changes
from app.research.page_proposal_review import PageDecisionBody, PageScope, ProposalPart, parts_in_scope

from ..research.page_report_rules_fixtures import FIGURE, PICTURE, page_document, sentence

ADDED_TEXT = "Iron turns the madder bath black where the block printed it."
NEW_STATEMENT = "Alum fixes the madder red at 70 degrees, and only where the block printed."


def changed(document: MonographDocument, edit: Any) -> MonographDocument:
    body = document.model_dump(mode="json", by_alias=True)
    edit(body)
    return MonographDocument.model_validate(body)


def marks(before: MonographDocument | None, after: MonographDocument) -> list[tuple[str, str, str, str]]:
    return [
        (chapter.key, change.kind, change.change, change.ref)
        for chapter in page_changes(before, after)
        for change in chapter.changes
    ]


def test_a_page_that_does_not_change_has_no_chapter_to_review() -> None:
    assert page_changes(page_document(), page_document()) == []


def test_an_added_sentence_is_marked_added_in_its_chapter_and_counted() -> None:
    after = page_document(extra={"chemistry-4": sentence("CHEMISTRY", ADDED_TEXT, "c6")})
    (chapter,) = page_changes(page_document(), after)
    assert (chapter.key, chapter.title) == ("chem", "The chemistry")
    assert (chapter.sentences.added, chapter.sentences.changed, chapter.sentences.removed) == (1, 0, 0)
    (change,) = chapter.changes
    assert (change.kind, change.change, change.before, change.after) == (
        "SENTENCE",
        "ADDED",
        None,
        ADDED_TEXT,
    )


def test_a_removed_sentence_is_marked_removed_with_what_it_said() -> None:
    before = page_document(extra={"chemistry-4": sentence("CHEMISTRY", ADDED_TEXT, "c6")})
    (chapter,) = page_changes(before, page_document())
    (change,) = chapter.changes
    assert (change.change, change.before, change.after) == ("REMOVED", ADDED_TEXT, None)


def test_a_reworded_sentence_shows_both_versions() -> None:
    def reword(body: dict[str, Any]) -> None:
        body["content"]["units"]["chemistry-1"]["nodes"] = [NEW_STATEMENT]

    (chapter,) = page_changes(page_document(), changed(page_document(), reword))
    (change,) = chapter.changes
    assert (change.change, change.ref, change.after) == ("CHANGED", "chemistry-1", NEW_STATEMENT)
    assert change.before == "Alum fixes the madder red at 70 degrees."


def test_a_component_new_to_the_page_and_a_recaptioned_picture_are_marked_as_such() -> None:
    def recaption(body: dict[str, Any]) -> None:
        body["content"]["units"]["u9001"]["nodes"] = ["The printer lifts the block"]

    def without_figure(body: dict[str, Any]) -> None:
        content = body["content"]
        content["components"] = [entry for entry in content["components"] if entry["label"] != FIGURE]
        content["layout"] = [
            entry for entry in content["layout"] if FIGURE not in (entry["ref"], entry["within"])
        ]
        body["specs"].pop(FIGURE)

    before = changed(page_document(), without_figure)
    after = changed(page_document(), recaption)
    found = marks(before, after)
    assert ("chem", "COMPONENT", "ADDED", FIGURE) in found
    assert ("opening", "PICTURE", "CHANGED", PICTURE) in found
    picture = next(
        change
        for chapter in page_changes(before, after)
        for change in chapter.changes
        if change.ref == PICTURE
    )
    assert (picture.before, picture.after) == ("The printer at work", "The printer lifts the block")
    assert marks(after, before) == [
        ("opening", "PICTURE", "CHANGED", PICTURE),
        ("chem", "COMPONENT", "REMOVED", FIGURE),
    ]


def test_a_new_page_has_everything_added_and_nothing_removed() -> None:
    found = marks(None, page_document())
    assert {change for _, _, change, _ in found} == {"ADDED"}
    assert ("chem", "COMPONENT", "ADDED", FIGURE) in found


def part(name: str, chapter: str | None, label: str | None = None) -> ProposalPart:
    kinds = {"fact": "FACTS", "component": "COMPONENTS", "layout": "LAYOUTS", "picture": "IMAGES"}
    return ProposalPart.model_validate(
        {
            "part": name,
            "kind": kinds[name],
            "id": uuid.uuid4(),
            "chapter": chapter,
            "label": label,
            "title": f"A {name}",
        }
    )


def test_a_chapter_s_decision_takes_only_that_chapter_s_parts_and_a_component_s_only_its_own() -> None:
    layout, table = part("layout", None), part("component", "chem", FIGURE)
    fact, history = part("fact", "chem"), part("fact", "history")
    parts = [layout, table, fact, history]
    chem = parts_in_scope(parts, PageScope(scope="CHAPTER", chapter="chem"))
    assert chem == [fact, table]
    assert parts_in_scope(parts, PageScope(scope="COMPONENT", label=FIGURE)) == [table]
    assert parts_in_scope(parts, PageScope()) == [fact, history, table, layout]
    assert parts_in_scope(parts, PageScope(scope="CHAPTER", chapter="why")) == []


@pytest.mark.parametrize(
    "refused",
    [
        {"scope": "CHAPTER", "action": "approve"},
        {"scope": "PAGE", "chapter": "chem", "action": "approve"},
        {"scope": "COMPONENT", "action": "approve"},
        {"scope": "PAGE", "action": "reject"},
        {"scope": "PAGE", "action": "reject", "note": "no"},
        {"scope": "PAGE", "action": "raise"},
    ],
)
def test_a_page_decision_names_its_scope_and_a_rejection_its_reason(refused: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PageDecisionBody.model_validate(refused)


def test_an_approval_may_leave_its_note_out_and_a_rejection_says_why() -> None:
    approval = PageDecisionBody.model_validate({"scope": "CHAPTER", "chapter": "chem", "action": "approve"})
    assert approval.scoped() == PageScope(scope="CHAPTER", chapter="chem")
    rejection = PageDecisionBody.model_validate({"action": "reject", "note": "The bath needs its source."})
    assert (rejection.scope, rejection.note) == ("PAGE", "The bath needs its source.")
