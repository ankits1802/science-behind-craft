import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.component_specs_general_svg import sanitised_svg
from app.research.component_specs_plates import SPEC_MODELS_PLATES
from app.research.component_specs_plates_parts import DrawingElement
from app.research.component_specs_science import SPEC_MODELS_SCIENCE
from app.research.component_specs_science_parts import SvgNode
from app.research.drawing_attributes import STYLE_PROPERTIES, drawing_attribute_problem

from . import science_spec_fixtures as fixtures

REPO = Path(__file__).resolve().parents[3]
CASES = json.loads((REPO / "shared" / "drawing.attributes.golden.json").read_text(encoding="utf-8"))
STORED = [
    REPO / "backend" / "app" / "data" / "monographs",
    REPO / "backend" / "app" / "data" / "kind_fixtures",
]
GOLDEN_DOCUMENT = REPO / "shared" / "monograph.document.golden.json"
BEACON = "background-image:url(https://attacker.example/p.png)"
DRAWINGS = (DrawingElement, SvgNode)


def _case_id(case: dict[str, str]) -> str:
    return f"{case['name']}={case['value']}"


def _drawn(model: type[DrawingElement | SvgNode], name: str, value: str) -> None:
    model.model_validate({"tag": "rect", "attrs": {name: value}})


def _attributes(value: Any) -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        attrs = value.get("attrs")
        if "tag" in value and isinstance(attrs, dict):
            yield from ((str(name), entry) for name, entry in attrs.items() if isinstance(entry, str))
        for item in value.values():
            yield from _attributes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _attributes(item)


def _label_card(seal_style: str) -> dict[str, Any]:
    seal = {"tag": "svg", "attrs": {"viewBox": "0 0 10 10", "style": seal_style}, "children": []}
    return {
        "variant": "gi",
        "kicker": "u0844",
        "seal": seal,
        "sentence": "u0846",
        "facts": [{"term": "u0852", "value": "u0853"}],
    }


def test_both_sides_hold_one_list_of_the_style_properties_a_drawing_may_set() -> None:
    assert sorted(STYLE_PROPERTIES) == CASES["styleProperties"]
    assert not {"position", "inset", "z-index", "cursor", "background-image", "content"} & STYLE_PROPERTIES


@pytest.mark.parametrize("model", DRAWINGS)
@pytest.mark.parametrize("case", CASES["kept"], ids=_case_id)
def test_a_drawing_keeps_its_paint_stroke_opacity_transform_text_and_in_drawing_references(
    model: type[DrawingElement | SvgNode], case: dict[str, str]
) -> None:
    assert drawing_attribute_problem(case["name"], case["value"]) is None
    _drawn(model, case["name"], case["value"])


@pytest.mark.parametrize("model", DRAWINGS)
@pytest.mark.parametrize("case", CASES["refused"], ids=_case_id)
def test_a_drawing_loads_nothing_from_another_address_and_lays_nothing_over_the_page(
    model: type[DrawingElement | SvgNode], case: dict[str, str]
) -> None:
    with pytest.raises(ValidationError):
        _drawn(model, case["name"], case["value"])


def test_a_label_card_seal_that_would_beacon_every_reader_is_refused_and_a_painted_one_is_kept() -> None:
    card = SPEC_MODELS_PLATES["label_card"]
    with pytest.raises(ValidationError, match="loads nothing from another address"):
        card.model_validate(_label_card(BEACON))
    with pytest.raises(ValidationError, match="never position"):
        card.model_validate(_label_card("position:fixed;inset:0;z-index:9999"))
    kept = card.model_validate(_label_card("fill:var(--dye-mud);opacity:1"))
    assert (
        kept.model_dump(mode="json", by_alias=True)["seal"]["attrs"]["style"]
        == "fill:var(--dye-mud);opacity:1"
    )


def test_a_reaction_player_scene_written_in_capitals_or_as_an_image_set_is_refused() -> None:
    for style in (
        "fill:URL(https://attacker.example/p.png)",
        'fill:image-set("https://attacker.example/p.png" 1x)',
    ):
        player = fixtures.reaction_player()
        player["scenes"] = [{**fixtures.DOT, "attrs": {**fixtures.DOT["attrs"], "style": style}}]
        with pytest.raises(ValidationError):
            SPEC_MODELS_SCIENCE["reaction_player"].model_validate(player)
    SPEC_MODELS_SCIENCE["reaction_player"].model_validate(fixtures.reaction_player())


def test_the_general_drawing_intake_drops_an_image_set_and_an_escape_and_keeps_a_token() -> None:
    markup = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect style="fill:image-set(&quot;https://attacker.example/p.png&quot; 1x)" width="2"/>'
        '<rect fill="\\75rl(https://attacker.example/p.png)" width="3"/>'
        '<rect style="fill: var(--ink-2)" clip-path="url(\'#c\')" width="4"/></svg>'
    )
    clean = sanitised_svg(markup)
    assert "attacker.example" not in clean
    assert 'style="fill: var(--ink-2)"' in clean
    assert "clip-path=\"url('#c')\"" in clean


def test_every_stored_drawing_passes_the_stricter_check() -> None:
    files = [path for root in STORED for path in sorted(root.rglob("*.json"))] + [GOLDEN_DOCUMENT]
    checked = 0
    for path in files:
        for name, value in _attributes(json.loads(path.read_text(encoding="utf-8"))):
            assert drawing_attribute_problem(name, value) is None, f"{path.name}: {name}={value!r}"
            checked += 1
    assert checked > 10_000
