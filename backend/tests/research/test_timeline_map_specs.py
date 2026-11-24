import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.data.kind_fixture_files import KIND_FIXTURES_DIR
from app.data.skill_library import reference_text
from app.models.component_kinds import AUTHORED_SCRIPT_KINDS, DECLARED_ONLY_KINDS
from app.research.component_specs import CONTRIBUTABLE_KINDS, MAP_POINTER, checked_spec, not_contributable
from app.research.component_specs_data_maps import TimelineMapSpec
from app.research.component_specs_either import DELIVERED_FORMS, declared_form
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.research.component_specs_timeline_map import (
    AREA_LAYERS,
    LAYERS_MAX,
    PHYSICAL_LAYERS,
    DeclaredTimelineMapSpec,
    TimelineMapPlace,
)
from app.research.component_specs_timeline_map_delivery import SERVER_SENT

MONOGRAPH_SPECS = (
    Path(__file__).resolve().parents[2] / "app" / "data" / "monographs" / "Kutch-Ajrakh" / "specs"
)
KUTCH_TIMELINE_MAP = MONOGRAPH_SPECS / "kutch-ajrakh__history__dated-record-timeline-map.json"
FACT = uuid.UUID("0b6f1d32-6c54-4f0e-9a51-1c2a4a0e8b11")
BIDAR = {"name": "u0002", "district": 529, "home": True}
HYDERABAD = {"name": "u0003", "district": 507}


def fixture() -> dict[str, Any]:
    return json.loads((KIND_FIXTURES_DIR / "timeline_map.json").read_text(encoding="utf-8"))


def label(text: str) -> DeliveredUnit:
    return DeliveredUnit(text=text)


def cited(text: str) -> DeliveredUnit:
    return DeliveredUnit(text=text, claim_ids=[FACT])


def route_map(
    text: str, *, years: tuple[int, int] = (1956, 1956)
) -> tuple[dict[str, Any], dict[str, DeliveredUnit]]:
    spec = {
        "head": {"title": "u0001"},
        "places": [BIDAR, HYDERABAD],
        "routes": [{"start": 0, "end": 1, "yearFrom": years[0], "yearTo": years[1], "text": "u0004"}],
    }
    units = {"u0001": label("Bidar to Hyderabad"), "u0002": label("Bidar"), "u0003": label("Hyderabad")}
    return spec, {**units, "u0004": cited(text)}


def test_the_timeline_map_is_delivered_in_its_declared_form_only() -> None:
    assert "timeline_map" in CONTRIBUTABLE_KINDS and len(CONTRIBUTABLE_KINDS) == 23
    assert DECLARED_ONLY_KINDS == ("timeline_map",) and AUTHORED_SCRIPT_KINDS == ("model_explainer",)
    assert not_contributable("timeline_map") is None
    assert not_contributable("model_explainer") == (
        "a model_explainer runs an authored page's own script; deliver a drawing or a diagram instead"
    )
    assert DELIVERED_FORMS["timeline_map"] is DeclaredTimelineMapSpec


def test_kutch_ajrakh_s_route_map_keeps_its_authored_form_and_is_never_delivered() -> None:
    authored = json.loads(KUTCH_TIMELINE_MAP.read_text(encoding="utf-8"))
    assert "head" in authored and "places" not in authored
    assert not declared_form("timeline_map", authored)
    assert isinstance(checked_spec("timeline_map", authored), TimelineMapSpec)
    (refused,) = spec_problems("timeline_map", authored, {})
    assert refused == f"a timeline_map without places is an authored page's own route map; {MAP_POINTER}"


def test_the_bidriware_fixture_is_the_declared_form() -> None:
    checked = checked_spec("timeline_map", fixture()["spec"])
    assert isinstance(checked, DeclaredTimelineMapSpec)
    assert [place.reference() for place in checked.places] == [
        "district:529",
        "district:507",
        "district:214",
        "district:319",
        "district:162",
    ]
    assert checked.used_places() == [0, 2, 3, 4, 0, 1]


@pytest.mark.parametrize(
    ("place", "problem"),
    [
        ({"name": "u0002", "district": 529, "wikidata": "Q461922"}, "a place is named one way"),
        ({"name": "u0002"}, "a place is named one way"),
        ({"name": "u0002", "longitude": 77.5, "latitude": 17.9}, "the unit at that cites them"),
        ({"name": "u0002", "wikidata": "Bidar"}, "String should match pattern"),
    ],
)
def test_a_place_is_named_by_its_item_its_district_or_a_cited_coordinate(
    place: dict[str, Any], problem: str
) -> None:
    spec = {"head": {"title": "u0001"}, "places": [place], "undated": [{"place": 0, "text": "u0003"}]}
    with pytest.raises(ValidationError, match=problem):
        checked_spec("timeline_map", spec)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"routes": []}, "with points, routes or undated facts"),
        (
            {"routes": [{"start": 0, "end": 2, "yearFrom": 1956, "yearTo": 1956, "text": "u0004"}]},
            "only its listed",
        ),
        (
            {"routes": [{"start": 0, "end": 0, "yearFrom": 1956, "yearTo": 1956, "text": "u0004"}]},
            "two different",
        ),
        (
            {"routes": [{"start": 0, "end": 1, "yearFrom": 1957, "yearTo": 1956, "text": "u0004"}]},
            "not after",
        ),
        ({"places": [BIDAR, HYDERABAD, {"name": "u0005", "district": 214}]}, "each listed place is named"),
        ({"places": [BIDAR, {**BIDAR, "name": "u0003"}]}, "lists each place once"),
        ({"layers": ["relief", "annual-precipitation"]}, "one area layer at a time"),
        ({"layers": ["rivers", "rivers"]}, "names each layer once"),
    ],
)
def test_a_timeline_map_dates_joins_or_captions_each_of_its_places_once(
    change: dict[str, Any], problem: str
) -> None:
    spec, _ = route_map("Many artisans from Bidar migrated to Hyderabad in 1956.")
    with pytest.raises(ValidationError, match=problem):
        checked_spec("timeline_map", {**spec, **change})


def test_rivers_and_minerals_lie_over_one_area_layer() -> None:
    spec, _ = route_map("Many artisans from Bidar migrated to Hyderabad in 1956.")
    checked = checked_spec("timeline_map", {**spec, "layers": ["relief", "rivers", "minerals"]})
    assert isinstance(checked, DeclaredTimelineMapSpec) and checked.layers == ["relief", "rivers", "minerals"]


def test_a_route_is_drawn_only_where_its_unit_states_the_move_and_its_years() -> None:
    spec, units = route_map("Many artisans from Bidar migrated to Hyderabad in 1956.")
    assert spec_problems("timeline_map", spec, units) == []
    unmoved, units = route_map("Bidar and Hyderabad held bidri workshops in 1956.")
    assert spec_problems("timeline_map", unmoved, units) == [
        "the unit u0004 of route 0 does not state the move from Bidar to Hyderabad"
    ]
    undated, units = route_map("Many artisans from Bidar migrated to Hyderabad.", years=(1956, 1957))
    assert spec_problems("timeline_map", undated, units) == [
        "the years 1956 to 1957 of route 0 are not stated by its unit u0004"
    ]


def test_a_point_names_its_place_and_a_coordinate_is_stated_by_a_cited_unit() -> None:
    places = [{"name": "u0002", "longitude": 77.52, "latitude": 17.91, "at": "u0003"}]
    spec = {"head": {"title": "u0001"}, "places": places}
    point = {"place": 0, "yearFrom": 1422, "yearTo": 1436, "text": "u0004"}
    units = {
        "u0001": label("Where bidri began"),
        "u0002": label("Bidar"),
        "u0003": cited("Bidar stands at 77.52 degrees east and 17.91 degrees north."),
        "u0004": cited("Bidri began at Bidar under a king who ruled from 1422 to 1436."),
    }
    assert spec_problems("timeline_map", {**spec, "points": [point]}, units) == []
    elsewhere = {**units, "u0004": cited("Bidri began under a king who ruled from 1422 to 1436.")}
    assert spec_problems("timeline_map", {**spec, "points": [point]}, elsewhere) == [
        "the unit u0004 of point 0 does not name its place 'Bidar'"
    ]
    rounded = {**units, "u0003": cited("Bidar stands at 77.5 degrees east and 17.91 degrees north.")}
    assert spec_problems("timeline_map", {**spec, "points": [point]}, rounded) == [
        "the coordinate 77.52 of place 0 is not stated by its unit u0003"
    ]
    uncited = {**units, "u0003": label("77.52 east, 17.91 north")}
    assert "the unit u0003 that places place 0 cites no fact" in spec_problems(
        "timeline_map", {**spec, "points": [point]}, uncited
    )


def test_a_spec_that_sends_the_server_s_placement_is_refused() -> None:
    spec, units = route_map("Many artisans from Bidar migrated to Hyderabad in 1956.")
    found = {"latitude": 17.766, "longitude": 77.144, "districtLgd": 529}
    placed = {**spec, "places": [{**BIDAR, "found": found}, HYDERABAD]}
    assert spec_problems("timeline_map", placed, units) == [SERVER_SENT]


def test_the_dataset_guide_names_the_ways_to_name_a_place_and_the_layers_a_map_may_ask_for() -> None:
    guide = " ".join(reference_text("datasets").split())
    maps = guide.split("## Maps of places")[1].split("## Contributed datasets")[0]
    named = {field.alias for name, field in TimelineMapPlace.model_fields.items() if name != "found"}
    assert named == {"name", "wikidata", "district", "longitude", "latitude", "at", "home"}
    for key in sorted(named - {"name"}):
        assert f"`{key}" in maps, key
    for layer in PHYSICAL_LAYERS:
        assert f"`{layer}`" in maps, layer
    assert AREA_LAYERS == ("relief",) and LAYERS_MAX == 3
    assert "at most one area layer" in maps and "`timeline_map`" in maps
