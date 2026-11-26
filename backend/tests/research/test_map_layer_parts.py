import uuid
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.data.map_layers import held_river_names, held_shapes
from app.research import component_specs_map_parts as parts
from app.research.component_specs import checked_spec
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.services.map_layer_places import held_map_problems

FACT = uuid.UUID("5e000000-0000-4000-8000-000000000003")
JAIPUR = 102
RAJASTHAN = 8
CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "data"
    / "contributor"
    / "contracts"
    / "component-specs-general.md"
)
OLD_SANGANERI: dict[str, Any] = {
    "head": {"title": "u0001", "caption": "u0002"},
    "places": [
        {"name": "u0003", "value": None, "reading": "u0004", "latitude": 26.82, "longitude": 75.79},
        {"name": "u0005", "value": None, "reading": "u0006", "latitude": 26.92, "longitude": 75.82},
        {"name": "u0007", "value": None, "reading": "u0008", "latitude": 26.82, "longitude": 75.55},
    ],
    "valueLabel": None,
}
PARTS: dict[str, Any] = {
    "frame": {"district": JAIPUR},
    "emphasis": {"layers": ["rivers"]},
    "routes": [{"start": 0, "end": 2, "text": "u0009"}],
    "rings": [{"place": 0, "radiusKm": 20, "text": "u0010"}],
    "districts": {
        "valueLabel": "u0011",
        "values": [
            {"district": JAIPUR, "value": 650, "reading": "u0012"},
            {"district": 110, "value": 410, "reading": "u0013"},
        ],
    },
    "sequence": [
        {"text": "u0014", "places": [0, 1]},
        {"text": "u0015", "routes": [0], "rings": [0], "districts": True},
    ],
}
MAP: dict[str, Any] = {**OLD_SANGANERI, **PARTS}
TEXTS = {
    "u0001": "Sanganer and the places around it",
    "u0002": "Sanganer lies south of Jaipur.",
    "u0003": "Sanganer",
    "u0004": "The GI's area of production.",
    "u0005": "Jaipur",
    "u0006": "Kishanpol Bazaar sells the prints.",
    "u0007": "Bagru",
    "u0008": "Bagru prints are set apart from Sanganeri.",
    "u0009": "Printers moved from Sanganer to Bagru.",
    "u0010": "The printers worked within 20 km of Sanganer.",
    "u0011": "Rain a year, mm",
    "u0012": "Jaipur district receives 650 mm of rain a year.",
    "u0013": "Sikar district receives 410 mm of rain a year.",
    "u0014": "Sanganer and Jaipur were the first centres.",
    "u0015": "The printers then moved out to Bagru.",
}
LABELS = {"u0001", "u0003", "u0005", "u0007", "u0011"}


def delivered(
    texts: dict[str, str] = TEXTS, uncited: frozenset[str] = frozenset()
) -> dict[str, DeliveredUnit]:
    return {
        ref: DeliveredUnit(text=text, claim_ids=[] if ref in LABELS or ref in uncited else [FACT])
        for ref, text in texts.items()
    }


def sanganeri_units() -> dict[str, DeliveredUnit]:
    return {ref: unit for ref, unit in delivered().items() if ref in {f"u000{n}" for n in range(1, 9)}}


def test_a_places_map_of_the_old_shape_still_validates_and_is_stored_exactly_as_it_came() -> None:
    checked = checked_spec("map_layer", OLD_SANGANERI)
    assert checked.model_dump(mode="json") == OLD_SANGANERI
    assert spec_problems("map_layer", OLD_SANGANERI, sanganeri_units()) == []


def test_a_map_asks_for_its_frame_routes_ring_district_values_and_sequence_beside_its_places() -> None:
    dumped = checked_spec("map_layer", MAP).model_dump(mode="json")
    assert dumped["frame"] == {"district": JAIPUR}
    assert dumped["rings"] == [{"place": 0, "radiusKm": 20.0, "text": "u0010"}]
    assert dumped["sequence"][1] == {
        "text": "u0015",
        "places": [],
        "routes": [0],
        "rings": [0],
        "districts": True,
    }
    assert spec_problems("map_layer", MAP, delivered()) == []


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"frame": {"district": JAIPUR, "places": [0]}}, "frame is chosen one way"),
        ({"frame": {}}, "frame is chosen one way"),
        ({"routes": [{"start": 1, "end": 1, "text": "u0009"}]}, "two different places"),
        (
            {"routes": [{"start": 0, "end": 7, "text": "u0009"}]},
            "route 0 names place 7, past the map's 3 places",
        ),
        ({"rings": [{"place": 0, "radiusKm": 0, "text": "u0010"}]}, "greater than 0"),
        (
            {"rings": [{"place": 0, "radiusKm": parts.RADIUS_KM_MAX + 1, "text": "u0010"}]},
            "less than or equal",
        ),
        ({"frame": {"places": [5]}}, "the frame names place 5"),
        (
            {"sequence": [{"text": "u0014", "places": [0]}, {"text": "u0015", "routes": [3]}]},
            "step 1 names a route past",
        ),
        (
            {"sequence": [{"text": "u0014", "places": [0]}, {"text": "u0015", "rings": [2]}]},
            "step 1 names a ring past",
        ),
        ({"sequence": [{"text": "u0014", "places": [0]}]}, "at least 2"),
        (
            {"sequence": [{"text": "u0014", "places": [0]}, {"text": "u0015"}]},
            "shows a place, a route, a ring",
        ),
        ({"emphasis": {}}, "names a layer, a river or a dam"),
        ({"emphasis": {"layers": ["sea"]}}, "relief"),
        (
            {
                "districts": {
                    "valueLabel": "u0011",
                    "values": [{"district": JAIPUR, "value": 1, "reading": "u0012"}] * 2,
                }
            },
            "one value",
        ),
    ],
)
def test_a_map_s_parts_are_drawable_or_refused(change: dict[str, Any], said: str) -> None:
    with pytest.raises(ValidationError, match=said):
        checked_spec("map_layer", {**MAP, **change})


def test_district_values_in_a_step_need_the_map_s_district_values() -> None:
    without = {key: value for key, value in MAP.items() if key != "districts"}
    with pytest.raises(ValidationError, match="step 1 shows the district values of a map that gives none"):
        checked_spec("map_layer", without)


@pytest.mark.parametrize(
    ("ref", "owner"),
    [("u0009", "route 0"), ("u0010", "ring 0"), ("u0012", f"district {JAIPUR}"), ("u0014", "step 0")],
)
def test_an_uncited_route_ring_value_or_step_is_refused(ref: str, owner: str) -> None:
    problems = spec_problems("map_layer", MAP, delivered(uncited=frozenset({ref})))
    assert f"the unit {ref} of {owner} cites no fact" in problems


def test_a_route_ring_or_value_its_unit_does_not_state_is_refused() -> None:
    texts = {
        **TEXTS,
        "u0009": "Bagru and Sanganer both print.",
        "u0010": "The printers worked close to Sanganer.",
        "u0012": "Jaipur district receives a good deal of rain.",
    }
    problems = spec_problems("map_layer", MAP, delivered(texts))
    assert "the unit u0009 of route 0 does not state the move from Sanganer to Bagru" in problems
    assert "the radius 20 km of ring 0 is not stated by its unit u0010" in problems
    assert f"the value 650 of district {JAIPUR} is not stated by its unit u0012" in problems


def test_a_frame_district_state_or_river_the_site_does_not_hold_is_refused_and_one_it_holds_is_not() -> None:
    assert JAIPUR in held_shapes().districts and RAJASTHAN in held_shapes().states
    assert "Chambal" in held_river_names()
    assert held_map_problems(checked_spec("map_layer", MAP)) == []
    held = checked_spec(
        "map_layer",
        {**MAP, "frame": {"state": RAJASTHAN}, "emphasis": {"rivers": ["Chambal", "Dravyavati"]}},
    )
    assert held_map_problems(held) == []
    unheld = checked_spec(
        "map_layer", {**MAP, "frame": {"district": 99999}, "emphasis": {"rivers": ["Saraswati of Sanganer"]}}
    )
    problems = held_map_problems(unheld)
    assert "the site holds no shape for the district with LGD code 99999" in problems
    assert any(
        problem.startswith("the site's rivers name no river 'Saraswati of Sanganer'") for problem in problems
    )
    stateless = held_map_problems(checked_spec("map_layer", {**MAP, "frame": {"state": 999}}))
    assert stateless == ["the site holds no shape for the state with LGD code 999"]


def test_the_contract_states_the_parts_limits() -> None:
    contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    for stated in (
        f"`routes`, 1 to {parts.ROUTES_MAX}",
        f"`rings`, 1 to {parts.RINGS_MAX}",
        f"up to {parts.RADIUS_KM_MAX:g} km",
        f"{parts.DISTRICT_VALUES_MIN} to {parts.DISTRICT_VALUES_MAX} districts",
        f"`sequence`, {parts.STEPS_MIN} to {parts.STEPS_MAX} steps",
        f"up to {parts.RIVERS_EMPHASISED_MAX} rivers",
    ):
        assert stated in contract, stated
    assert ", ".join(f"`{layer}`" for layer in parts.EMPHASIS_LAYERS) in contract
