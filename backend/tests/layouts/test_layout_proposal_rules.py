from typing import Any

import pytest
from pydantic import ValidationError

from app.research.layout_proposals import LayoutProposalDraft, layout_changes
from app.research.page_layout import PageLayoutEntry

HERO = {"ref": "kutch-ajrakh/pictures/i01", "chapter": "glance", "order": 1, "role": "HERO"}
PLATE = {"ref": "kutch-ajrakh/pictures/i02", "chapter": "made", "order": 2, "role": "PLATE"}
QUOTE = {"ref": "history-0a1b2c3d4e", "chapter": "history", "order": 1, "role": "PULL_QUOTE"}
SIDE = {"ref": "kutch-ajrakh/market/prices", "chapter": "custom-notes", "order": 1, "role": "SIDEBAR"}


def entries(*items: dict[str, Any]) -> list[PageLayoutEntry]:
    return [PageLayoutEntry.model_validate(item) for item in items]


def draft(*items: dict[str, Any], **changes: Any) -> LayoutProposalDraft:
    body = {"subject": {"kind": "craft", "slug": "Kutch-Ajrakh"}, "baseVersion": 2, "entries": list(items)}
    return LayoutProposalDraft.model_validate(body | changes)


def test_a_proposal_is_a_whole_layout_built_on_a_version_with_an_optional_note() -> None:
    proposal = draft(HERO, PLATE, note="Lead with the resist print.")
    assert (proposal.subject.kind, proposal.base_version, len(proposal.entries)) == ("craft", 2, 2)
    assert draft(baseVersion=0).entries == []
    assert draft(HERO, subject={"kind": "family", "slug": "Ajrakh"}).subject.kind == "family"


@pytest.mark.parametrize(
    ("changes", "said"),
    [
        ({"entries": [HERO, HERO | {"order": 2}]}, "places each unit or component once"),
        ({"entries": [HERO, PLATE | {"role": "HERO"}]}, "one HERO"),
        ({"entries": [QUOTE | {"role": "PLATE"}]}, "is a text unit"),
        ({"baseVersion": -1}, "greater than or equal to 0"),
        ({"subject": {"kind": "district", "slug": "Kachchh"}}, "subject.kind"),
        ({"note": ""}, "at least 1 character"),
        ({"entries": [HERO], "facts": ["a fact"]}, "Extra inputs are not permitted"),
    ],
)
def test_a_proposal_that_breaks_a_layout_rule_is_refused_before_it_is_stored(
    changes: dict[str, Any], said: str
) -> None:
    with pytest.raises(ValidationError, match=said):
        draft(**changes)


def test_the_changes_say_what_is_placed_moved_and_taken_out_in_reading_order() -> None:
    current = entries(PLATE, SIDE, QUOTE)
    moved = PLATE | {"chapter": "chem", "order": 1, "role": "FIGURE"}
    proposed = entries(SIDE, QUOTE, HERO, moved)
    found = layout_changes(current, proposed)
    assert [(change.ref, change.change) for change in found] == [
        (HERO["ref"], "ADDED"),
        (PLATE["ref"], "CHANGED"),
    ]
    assert found[1].before == entries(PLATE)[0] and found[1].after == entries(moved)[0]
    taken = layout_changes(current, entries(QUOTE))
    assert [(change.ref, change.change, change.after) for change in taken] == [
        (PLATE["ref"], "REMOVED", None),
        (SIDE["ref"], "REMOVED", None),
    ]


def test_a_first_layout_places_everything_and_the_same_layout_changes_nothing() -> None:
    assert [change.change for change in layout_changes([], entries(HERO, PLATE))] == ["ADDED", "ADDED"]
    assert layout_changes(entries(HERO, PLATE), entries(PLATE, HERO)) == []
