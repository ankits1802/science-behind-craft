import uuid
from typing import Any

import pytest

from app.research.blocks_play import SIMULATION_VALUES_MAX
from app.research.citations import Citation
from app.research.simulation_draft import (
    SimulationDraft,
    checked_draft,
    data_object,
    offered_values,
    stated_figures,
)

from .fixtures import BUILT_AT, OPUS, WATER_STATED, accepted_html, draft, water_citation


def citation(quote: str, claim: int = 1) -> Citation:
    return Citation.model_validate(
        water_citation() | {"claimId": str(uuid.UUID(int=claim)), "quote": quote, "id": f"cite-{claim}"}
    )


def checked(reply: dict[str, Any]) -> Any:
    offers = offered_values([Citation.model_validate(water_citation())])
    return checked_draft(
        SimulationDraft.model_validate(reply),
        offers,
        block_id="s1.simulation",
        model=OPUS,
        created_at=BUILT_AT,
    )


def test_each_figure_a_quote_states_is_offered_with_the_three_words_either_side() -> None:
    offers = offered_values([Citation.model_validate(water_citation())])
    assert [(o.ref, o.figure, o.value, o.stated) for o in offers] == [
        ("v1", "10", 10.0, WATER_STATED),
        ("v2", "15", 15.0, WATER_STATED),
    ]
    assert {str(offer.claim_id) for offer in offers} == {water_citation()["claimId"]}


def test_the_stated_words_stop_at_a_clause_and_keep_the_unit() -> None:
    quote = "Mordanting baths of 8 g/L alum were heated to 60 °C, then cooled."
    assert list(stated_figures(quote)) == [
        ("8", 8.0, "Mordanting baths of 8 g/L alum were"),
        ("60", 60.0, "were heated to 60 °C"),
    ]


def test_formula_digits_and_figures_with_no_plain_value_are_not_offered() -> None:
    assert [figure for figure, _, _ in stated_figures("Fe2O3 forms near 600 degrees.")] == ["600"]
    assert list(stated_figures("1.234.567 pieces")) == []
    assert list(stated_figures("")) == []


def test_a_figure_is_offered_once_per_claim_and_the_offer_is_capped() -> None:
    many = [
        citation(" ".join(f"{n} m." for n in range(start, start + 10)), start) for start in range(3, 63, 10)
    ]
    offers = offered_values([citation("10 and 10 again."), citation("10 too.", claim=2), *many])
    assert [(o.ref, o.value, o.citation.claim_id) for o in offers[:2]] == [
        ("v1", 10.0, str(uuid.UUID(int=1))),
        ("v2", 10.0, str(uuid.UUID(int=2))),
    ]
    assert len(offers) == SIMULATION_VALUES_MAX
    assert offers[-1].ref == f"v{SIMULATION_VALUES_MAX}"


def test_a_draft_using_offered_values_becomes_a_block_with_its_data_object() -> None:
    check = checked(draft(accepted_html()))
    assert check.problems == ()
    assert check.block is not None
    assert data_object(check.block.values) == {"fallLowFeet": 10.0, "fallHighFeet": 15.0}
    assert [(v.unit, v.stated) for v in check.block.values] == [("feet", WATER_STATED)] * 2


@pytest.mark.parametrize(
    ("changes", "rule", "detail"),
    [
        (
            {"values": [{"ref": "v9", "key": "fall", "label": "Fall", "unit": ""}]},
            "VALUE",
            "v9 is not an offered",
        ),
        ({"values": []}, "VALUE", "no offered value is used"),
        (
            {"values": [{"ref": "v1", "key": "a", "label": "A", "unit": ""}] * 2},
            "VALUE",
            "v1 is used twice",
        ),
        (
            {"values": [{"ref": "v1", "key": "fall", "label": "Fall", "unit": "metres"}]},
            "VALUE",
            "gives the unit 'metres'",
        ),
        (
            {"values": [{"ref": "v1", "key": "fall", "label": "Fall of 12 feet", "unit": ""}]},
            "VALUE",
            "labelled with a figure",
        ),
        ({"values": [{"ref": "v1", "key": "Fall", "label": "Fall", "unit": ""}]}, "VALUE", "pattern"),
        ({"title": "The 20 foot fall"}, "BLOCK", "titles itself with a figure"),
        ({"concept": "जल"}, "BLOCK", "no Latin letter or digit"),
    ],
)
def test_a_draft_off_the_rules_names_what_it_breaks(changes: dict[str, Any], rule: str, detail: str) -> None:
    check = checked(draft("<p>Water</p>", **changes))
    assert check.block is None
    assert check.rules == (rule,)
    assert any(detail in problem.detail for problem in check.problems)


def test_the_static_check_runs_on_the_draft_s_own_data_object() -> None:
    assert checked(draft("<script>const fall = 15;</script>")).problems == ()
    refused = checked(draft("<script>const fall = 17;</script>"))
    assert (refused.block, refused.rules) == (None, ("NUMBER",))
