import copy
import uuid
from typing import Any

import pytest

from app.data.kind_fixture_files import kind_fixtures
from app.research.component_specs_general_delivery import DeliveredComponent, DeliveredUnit, spec_problems
from app.research.spec_strings import spec_strings
from app.research.spec_text_units import text_units_resolved
from app.research.unit_ids import UNIT_REF
from app.services.component_proposals_drawn import DrawnDelivery, drawn_delivery

PLACE = ("chem", "CHEMISTRY")
ADDED = "u0900"
Path = tuple[str | int, ...]
TEXT_PLACES: dict[str, Path] = {
    "blue-pottery-of-jaipur/market/at-a-glance": ("tiles", 1, "figure"),
    "blue-pottery-of-jaipur/policy/where-sources-differ": ("items", 0, "summary", 0),
    "bidriware/chemistry/what-blackens": ("options", 0, "label"),
    "bidriware/chemistry/why-copper": ("options", 1, "label"),
    "bidriware/chemistry/fort-earth-dip": ("stripLabel",),
    "cane-bamboo-craft/chemistry/lime-wash": ("line", "reactants", 0, "name"),
    "bidriware/chemistry/what-if-lab": ("pickerLabel",),
    "blue-pottery-of-jaipur/materials/glaze-and-colour": ("heading",),
    "bidriware/chemistry/ammonium-chloride": ("molecules", 0, "name"),
    "bidriware/chemistry/patina-steps": ("steps", 0, "name"),
    "bastar-dhokra/process/student-version": ("summary",),
    "bastar-dhokra/process/lost-wax-stages": ("stages", 0, "name"),
    "bidriware/chemistry/patina-salts": ("molecules", 0, "drawing", "children", 4, "children", 0),
    "bastar-dhokra/process/core-before-and-after-sem": ("swatches", 0, "label"),
    "bidriware/people/copper-for-the-black": ("testimony", "evidence"),
}
FIXTURES = {fixture["label"]: fixture for fixture in kind_fixtures()}


def _at(value: Any, path: Path) -> Any:
    for step in path:
        value = value[step]
    return value


def _put(spec: dict[str, Any], path: Path, new: Any) -> dict[str, Any]:
    changed = copy.deepcopy(spec)
    _at(changed, path[:-1])[path[-1]] = new
    return changed


def _units(fixture: dict[str, Any]) -> dict[str, DeliveredUnit]:
    ids = {key: uuid.uuid5(uuid.NAMESPACE_URL, f"{fixture['craft']}/{key}") for key in fixture["facts"]}
    return {
        ref: DeliveredUnit(text=unit["text"], claim_ids=[ids[claim] for claim in unit["claims"]])
        for ref, unit in fixture["units"].items()
    }


def _drawn(kind: str, spec: dict[str, Any], units: dict[str, DeliveredUnit]) -> DrawnDelivery:
    visible = {claim: None for unit in units.values() for claim in unit.claim_ids}
    drawn = drawn_delivery(
        kind, DeliveredComponent(spec=spec, units=units), place=PLACE, visible=visible, taken=()
    )
    assert drawn is not None
    return drawn


def _refs(spec: dict[str, Any]) -> set[str]:
    return {value for value in spec_strings(spec) if UNIT_REF.match(value)}


def test_every_kind_fixture_is_proven_here() -> None:
    assert set(FIXTURES) >= set(TEXT_PLACES)
    assert len(FIXTURES) == 28


@pytest.mark.parametrize("label", sorted(FIXTURES))
def test_each_kind_draws_every_unit_it_names_from_the_page_s_units(label: str) -> None:
    fixture = FIXTURES[label]
    units = _units(fixture)
    drawn = _drawn(fixture["kind"], fixture["spec"], units)
    assert _refs(drawn.spec) == set(drawn.drafts)
    assert len(drawn.drafts) == len(units)
    assert sorted(draft.text for draft in drawn.drafts.values()) == sorted(
        unit.text for unit in units.values()
    )


@pytest.mark.parametrize("label", sorted(TEXT_PLACES))
def test_a_unit_named_where_a_kind_draws_plain_words_is_drawn_as_its_words(label: str) -> None:
    fixture = FIXTURES[label]
    path = TEXT_PLACES[label]
    words = _at(fixture["spec"], path)
    assert isinstance(words, str) and not UNIT_REF.match(words)
    spec = _put(fixture["spec"], path, ADDED)
    units = {**_units(fixture), ADDED: DeliveredUnit(text=words)}
    assert spec_problems(fixture["kind"], spec, units) == []
    drawn = _drawn(fixture["kind"], spec, units)
    added = max(drawn.drafts)
    assert drawn.drafts[added].text == words
    assert _at(drawn.spec, path) == words
    assert _refs(drawn.spec) == set(drawn.drafts) - {added}


def test_the_stat_tiles_a_contributor_wrote_draw_their_numbers_not_their_unit_ids() -> None:
    spec = {"classes": [], "tiles": [{"figure": "u0001", "small": "u0002", "caption": "u0003"}]}
    texts = {"u0001": "315", "u0002": "units", "u0003": "The GI application counted 315 printing units."}
    assert text_units_resolved("stat_tiles", spec, texts) == {
        "classes": [],
        "tiles": [{"figure": "315", "small": "units", "caption": "u0003"}],
    }


def test_words_that_are_no_unit_of_the_component_stay_as_they_are() -> None:
    spec = {"classes": [], "tiles": [{"figure": "u0009", "small": "units", "caption": "u0003"}]}
    texts = {"u0003": "The GI application counted 315 printing units."}
    assert text_units_resolved("stat_tiles", spec, texts) == spec


def test_a_unit_named_in_a_unit_s_place_keeps_its_id_for_the_page_to_cite() -> None:
    spec = {
        "id": "s-differ",
        "titleId": "s-differ-t",
        "title": "u0001",
        "intro": "u0002",
        "items": [
            {
                "summary": ["u0003", {"m": "b", "c": ["u0004"]}],
                "readings": [{"who": "u0005", "unit": "u0006"}, {"who": "Impart", "unit": "u0007"}],
            }
        ],
    }
    texts = {
        ref: f"words of {ref}" for ref in ("u0001", "u0002", "u0003", "u0004", "u0005", "u0006", "u0007")
    }
    resolved = text_units_resolved("source_disagreements", spec, texts)
    assert resolved["title"] == "words of u0001"
    assert resolved["intro"] == "u0002"
    assert resolved["items"][0]["summary"] == ["words of u0003", {"m": "b", "c": ["words of u0004"]}]
    assert resolved["items"][0]["readings"] == [
        {"who": "words of u0005", "unit": "u0006"},
        {"who": "Impart", "unit": "u0007"},
    ]
