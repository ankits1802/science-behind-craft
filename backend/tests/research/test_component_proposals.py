from typing import Any

import pytest
from pydantic import ValidationError

from app.research.component_proposals import (
    ComponentProposalDraft,
    close_matches,
    content_words,
    match_reasons,
    task_problem,
    word_overlap,
)
from app.research.knowledge_api import ComponentSubject, ComponentSummary

TANNIC_ACID = "0c000000-0000-4000-8000-000000000001"
ALUM = "0c000000-0000-4000-8000-000000000002"


def draft(**changes: Any) -> ComponentProposalDraft:
    values: dict[str, Any] = {
        "label": "shared/chemistry/tannic-acid-molecule",
        "title": "Tannic acid molecule",
        "description": "A turnable 3D model of tannic acid, the tannin of myrobalan that binds iron and alum.",
        "kind": "molecule_3d",
        "field": "CHEMISTRY",
        "subjects": [{"kind": "COMPOUND", "key": TANNIC_ACID}],
    }
    return ComponentProposalDraft.model_validate({**values, **changes})


def summary(**changes: Any) -> ComponentSummary:
    values: dict[str, Any] = {
        "label": "kutch-ajrakh/chemistry/indigo-redox-player",
        "title": "Indigo reduction and oxidation",
        "description": "A player that steps indigo through its reduction to leucoindigo in the vat and back in air.",
        "kind": "reaction_player",
        "field": "CHEMISTRY",
        "fields": [],
        "craft_slug": "Kutch-Ajrakh",
        "subjects": [ComponentSubject(kind="CRAFT", key="Kutch-Ajrakh", name="Kutch Ajrakh")],
    }
    return ComponentSummary.model_validate({**values, **changes})


def test_content_words_drop_short_and_common_words() -> None:
    assert content_words("The Indigo vat: how it shows a reduction, in 3D!") == frozenset(
        {"indigo", "vat", "reduction"}
    )


def test_word_overlap_is_shared_words_over_all_words() -> None:
    first = frozenset({"tannic", "acid", "molecule"})
    second = frozenset({"tannic", "acid", "structure", "model"})
    assert word_overlap(first, second) == pytest.approx(2 / 5)
    assert word_overlap(frozenset(), frozenset()) == 0.0


def test_the_same_kind_keyed_to_the_same_compound_is_a_close_match() -> None:
    held = summary(
        label="shared/chemistry/tannin-structure",
        title="Tannin structure",
        description="The gallotannin structure turned in three dimensions.",
        kind="molecule_3d",
        craft_slug=None,
        subjects=[ComponentSubject(kind="COMPOUND", key=TANNIC_ACID, name="Tannic acid")],
    )
    assert match_reasons(draft(), held) == ["the same kind, keyed to the same compound Tannic acid"]


def test_the_same_kind_on_the_same_craft_with_another_topic_is_not_a_match() -> None:
    proposed = draft(
        label="kutch-ajrakh/chemistry/alum-mordant-player",
        title="Alum mordant bath",
        description="A player that shows how alum fixes the madder red to cotton in the mordant bath.",
        kind="reaction_player",
        subjects=[{"kind": "CRAFT", "key": "Kutch-Ajrakh"}, {"kind": "CONCEPT", "key": ALUM}],
    )
    assert match_reasons(proposed, summary()) == []


def test_a_title_sharing_half_its_words_in_the_same_kind_is_a_close_match() -> None:
    proposed = draft(
        label="kutch-ajrakh/chemistry/indigo-reduction-steps",
        title="Indigo reduction steps",
        description="Stepping the dye from blue to yellow-green leucoindigo with lime and jaggery in the vat.",
        kind="reaction_player",
        subjects=[{"kind": "CRAFT", "key": "Kutch-Ajrakh"}],
    )
    assert match_reasons(proposed, summary()) == ["the same kind with a title sharing 50% of its words"]


def test_a_near_copy_of_any_kind_is_a_close_match_and_the_same_label_always_is() -> None:
    copy = draft(
        label="kutch-ajrakh/chemistry/indigo-redox-player",
        title="Indigo reduction and oxidation",
        description="A player that steps indigo through its reduction to leucoindigo in the vat and back in air.",
        kind="diagram",
        subjects=[{"kind": "CRAFT", "key": "Kutch-Ajrakh"}],
    )
    assert match_reasons(copy, summary()) == [
        "it already has this label",
        "a title and description sharing 100% of their words",
    ]


def test_the_component_extended_is_never_its_own_match_and_each_label_counts_once() -> None:
    held = summary(
        label="shared/chemistry/tannic-acid-molecule",
        kind="molecule_3d",
        subjects=[ComponentSubject(kind="COMPOUND", key=TANNIC_ACID, name="Tannic acid")],
    )
    plain = draft(label="shared/chemistry/tannic-acid-molecule-2")
    assert [match.component.label for match in close_matches(plain, [held, held])] == [held.label]
    link = draft(extends=held.label, extension="SUBJECT_LINK", label=held.label)
    assert close_matches(link, [held]) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"extends": "shared/chemistry/tannin-structure"}, "come together"),
        ({"extends": "shared/chemistry/tannin-structure", "extension": "SUBJECT_LINK"}, "keeps the label"),
        (
            {
                "label": "shared/chemistry/tannin-structure",
                "extends": "shared/chemistry/tannin-structure",
                "extension": "VARIANT",
            },
            "label of its own",
        ),
        ({"fields": ["CHEMISTRY"]}, "never the main field"),
        (
            {
                "subjects": [
                    {"kind": "COMPOUND", "key": TANNIC_ACID},
                    {"kind": "COMPOUND", "key": TANNIC_ACID},
                ]
            },
            "once",
        ),
        ({"label": "Tannic Acid"}, "label"),
        ({"description": "Too short."}, "description"),
        ({"subjects": []}, "subjects"),
    ],
)
def test_a_malformed_proposal_is_refused(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        draft(**changes)


ON_AJRAKH = [{"kind": "CRAFT", "key": "Kutch-Ajrakh"}, {"kind": "COMPOUND", "key": TANNIC_ACID}]


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({}, None),
        ({"task_key": "MISSING_COMPONENT:craft:Kutch-Ajrakh:molecules", "subjects": ON_AJRAKH}, None),
        (
            {"task_key": "MISSING_COMPONENT:craft:Kutch-Ajrakh:molecules", "craft_slug": "Kutch-Ajrakh"},
            None,
        ),
        ({"task_key": "PAGE_FORM:craft:Kutch-Ajrakh", "subjects": ON_AJRAKH}, "not a missing-component task"),
        ({"task_key": "MISSING_COMPONENT:craft:Kutch-Ajrakh:map", "subjects": ON_AJRAKH}, "kind map_layer"),
        (
            {"task_key": "MISSING_COMPONENT:craft:Bidriware:molecules", "subjects": ON_AJRAKH},
            "craft Bidriware",
        ),
    ],
)
def test_a_proposal_completes_only_the_missing_component_task_it_fills(
    changes: dict[str, Any], says: str | None
) -> None:
    problem = task_problem(draft(**changes))
    assert problem is None if says is None else (problem is not None and says in problem)
