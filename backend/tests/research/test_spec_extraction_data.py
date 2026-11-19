import json
import re
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.component_specs_data import SPEC_MODELS_DATA
from app.research.monograph_page import MonographContent
from app.scripts.build_monograph import monograph_content
from app.scripts.extract_specs_data import DATA, bar_share
from app.scripts.extract_specs_files import extracted_specs, spec_path, stale_specs

SLUG = "Kutch-Ajrakh"
UNIT_ID = re.compile(r"^u\d{4}$")
YARD = (
    '<main><figure class="yard" aria-labelledby="yd-t"><p class="fig-no" data-fig="pt:7"><kv-slot unit="u0839"></kv-slot></p>'
    '<p class="chart-title" id="yd-t"><kv-slot unit="u0840"></kv-slot></p>'
    '<div class="yard-row"><span>Fabindia, New Delhi</span><span class="yb emph" style="width:100%"></span><b>70,000 m</b></div>'
    '<div class="yard-row"><span>Maiwa, Vancouver</span><span class="yb" style="width:1.43%;min-width:2px"></span><b>1,000 m</b></div>'
    '<p class="src-line"><kv-slot unit="u0841"></kv-slot></p></figure>'
    '<div class="ws-stats"><div class="mk-stat"><span class="t-stat">2007</span><p><kv-slot unit="u0628"></kv-slot></p></div></div></main>'
)


def _component(label: str, kind: str, anchor: str) -> dict[str, Any]:
    return {
        "label": label,
        "chapter": "market",
        "anchor": anchor,
        "kind": kind,
        "title": label,
        "description": label,
        "field": "ECONOMICS",
        "fields": [],
        "subjects": [],
    }


def _content(*components: dict[str, Any]) -> MonographContent:
    return MonographContent.model_validate(
        {
            "craftSlug": SLUG,
            "sources": {},
            "citations": {},
            "citationClaims": {},
            "data": {},
            "units": {},
            "components": list(components),
            "layout": [],
        }
    )


def _units(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if UNIT_ID.match(value) else set()
    if isinstance(value, dict):
        return set().union(set(), *(_units(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(set(), *(_units(item) for item in value))
    return set()


def test_a_bar_is_drawn_to_its_share_of_the_largest_to_two_places() -> None:
    assert bar_share(1000, 70000) == "1.43%"
    assert bar_share(70000, 70000) == "100%"
    assert bar_share(1, 3) == "33.33%"


def test_bar_rows_become_their_values_and_figure_head() -> None:
    content = _content(_component("kutch-ajrakh/economics/yardage", "chart", '[aria-labelledby="yd-t"]'))
    spec = extracted_specs(DATA, content, YARD)["kutch-ajrakh/economics/yardage"].model_dump(
        mode="json", by_alias=True
    )
    assert spec["rows"]["head"] == {
        "number": {"unit": "u0839", "ref": "pt:7"},
        "title": "u0840",
        "titleId": "yd-t",
        "dek": None,
        "dekId": None,
    }
    assert [(row["label"], row["value"], row["emphasis"]) for row in spec["rows"]["rows"]] == [
        ("Fabindia, New Delhi", 70000.0, True),
        ("Maiwa, Vancouver", 1000.0, False),
    ]


def test_a_bar_drawn_off_its_share_is_refused() -> None:
    content = _content(_component("kutch-ajrakh/economics/yardage", "chart", '[aria-labelledby="yd-t"]'))
    with pytest.raises(InvalidInput, match="share of the largest"):
        extracted_specs(DATA, content, YARD.replace("width:1.43%", "width:2%"))


def test_a_component_holding_another_its_spec_does_not_name_is_refused() -> None:
    held = YARD.replace(
        '<p class="src-line">',
        '<div class="ws-stats"><div class="mk-stat"><span class="t-stat">2</span><p><kv-slot unit="u0001"></kv-slot></p></div></div><p class="src-line">',
    )
    held = held.replace(
        '<div class="ws-stats"><div class="mk-stat"><span class="t-stat">2007',
        '<div class="other"><div class="mk-stat"><span class="t-stat">2007',
    )
    content = _content(
        _component("kutch-ajrakh/economics/yardage", "chart", '[aria-labelledby="yd-t"]'),
        _component("kutch-ajrakh/economics/stats", "stat_tiles", '[class="ws-stats"]'),
    )
    with pytest.raises(InvalidInput, match="holds the components"):
        extracted_specs(DATA, content, held)


@pytest.fixture(scope="module")
def ajrakh() -> MonographContent:
    return monograph_content(SLUG)


def test_every_ajrakh_data_component_has_a_spec_file_that_validates(ajrakh: MonographContent) -> None:
    data = [component for component in ajrakh.components if component.kind in SPEC_MODELS_DATA]
    assert len(data) == 25
    for component in data:
        SPEC_MODELS_DATA[component.kind].model_validate_json(
            spec_path(SLUG, component.label).read_bytes().decode("utf-8")
        )


def test_each_ajrakh_data_spec_shows_exactly_the_units_its_component_holds(ajrakh: MonographContent) -> None:
    for component in ajrakh.components:
        if component.kind not in SPEC_MODELS_DATA:
            continue
        spec = json.loads(spec_path(SLUG, component.label).read_bytes().decode("utf-8"))
        within = {
            entry.ref for entry in ajrakh.layout if entry.kind == "unit" and entry.within == component.label
        }
        assert _units(spec) == within, component.label


def test_the_committed_data_specs_are_what_extraction_writes() -> None:
    assert stale_specs(DATA, SLUG) == []
