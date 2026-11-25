import copy
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.data.kind_fixture_files import kind_fixtures
from app.research.component_specs import checked_spec
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.research.drawn_art import (
    KIT_POINTER,
    MATERIAL_PARTS,
    SCENE_POINTER,
    drawn_art_problems,
    free_drawings,
    scene_problems,
)

APP = Path(__file__).resolve().parents[2] / "app"
MONOGRAPH_SPECS = APP / "data" / "monographs" / "Kutch-Ajrakh" / "specs"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400">{}</svg>'
TEXTS = {"u0001": "Wax strings on the model", "u0003": "Wax strings wound in close turns"}
UNITS = {
    "u0001": DeliveredUnit(
        text="Wax strings on the model", claim_ids=[uuid.UUID("5d4a7f0e-6a1e-4c1b-9b8e-2f7d3c9a1b20")]
    ),
    "u0003": DeliveredUnit(text="Wax strings wound in close turns"),
}
AT_THE_KIT = SCENE_POINTER.format(kind="stage_player")


def rects(count: int, *, stroke: str = ' stroke="var(--ink-1)"') -> str:
    return "".join(
        f'<rect x="{10 + 20 * at}" y="10" width="16" height="16" fill="var(--sunk)"{stroke}/>'
        for at in range(count)
    )


def declared(body: str) -> dict[str, Any]:
    return {"head": {"title": "u0001"}, "svg": SVG.format(body), "alt": "u0003"}


def found(kind: str, spec: dict[str, Any], texts: dict[str, str] = TEXTS) -> list[str]:
    return drawn_art_problems(kind, checked_spec(kind, spec).model_dump(mode="json"), texts)


def scene_found(kind: str, spec: dict[str, Any], texts: dict[str, str] = TEXTS) -> list[str]:
    return scene_problems(kind, checked_spec(kind, spec).model_dump(mode="json"), texts)


def stage_player(children: list[dict[str, Any]]) -> dict[str, Any]:
    fixture = next(fixture for fixture in kind_fixtures() if fixture["kind"] == "stage_player")
    spec = copy.deepcopy(fixture["spec"])
    spec["drawing"] = {"tag": "svg", "attrs": {"viewBox": "0 0 320 200"}, "children": children}
    return spec


def inked_rects(count: int) -> list[dict[str, Any]]:
    return [
        {
            "tag": "rect",
            "attrs": {
                "x": str(10 + 20 * at),
                "y": "10",
                "width": "16",
                "height": "16",
                "fill": "var(--sunk)",
                "stroke": "var(--ink-1)",
            },
        }
        for at in range(count)
    ]


SOIL = {"cx": "100", "cy": "120", "rx": "40", "ry": "50"}


@pytest.mark.parametrize("size", ["24", "26", "28", "32"])
def test_text_at_the_type_scale_s_ui_sizes_is_kept(size: str) -> None:
    body = rects(6) + f'<text x="10" y="200" font-size="{size}" fill="var(--ink-1)">Wax</text>'
    assert found("drawing", declared(body)) == []


def test_text_in_a_scaled_group_is_measured_as_drawn() -> None:
    body = (
        rects(6)
        + '<g transform="scale(0.5)"><text x="20" y="300" font-size="56" fill="var(--ink-1)">Wax</text></g>'
    )
    assert found("drawing", declared(body)) == []


@pytest.mark.parametrize(("size", "drawn"), [("30", "15.0"), ("40", "20.0"), ("25", "12.5")])
def test_text_off_the_type_scale_is_refused_with_the_sizes_to_set(size: str, drawn: str) -> None:
    body = rects(6) + f'<text x="10" y="200" font-size="{size}" fill="var(--ink-1)">Wax</text>'
    assert found("drawing", declared(body)) == [
        f"the drawing: the text 'Wax' is drawn at {drawn} px when the drawing is 320 px wide, off the type "
        "scale; set it at 24, 26, 28, 32 units (the scale's 12, 13, 14 or 16 px), or give the words as a "
        "unit, as the kit's labels are"
    ]


def test_a_figure_of_fewer_than_six_shapes_is_refused_and_six_are_enough() -> None:
    assert found("drawing", declared(rects(5))) == [
        f"the drawing draws 5 shapes, fewer than the 6 a figure at the bar is drawn with; {KIT_POINTER}"
    ]
    assert found("drawing", declared(rects(6))) == []
    pattern = '<defs><pattern id="p" width="4" height="4"><path d="M0 0 L4 4" stroke="var(--ink-1)"/></pattern></defs>'
    assert "draws 5 shapes" in found("drawing", declared(pattern + rects(5)))[0]


def test_a_figure_with_no_line_work_in_ink_is_refused_and_a_group_s_ink_counts() -> None:
    flat = rects(6, stroke="")
    assert found("drawing", declared(flat)) == [
        f"the drawing has no line work in ink: edge what it shows in --ink-1, --ink-2 or --ink-3; {KIT_POINTER}"
    ]
    assert found("drawing", declared(f'<g stroke="var(--ink-2)">{flat}</g>')) == []
    assert found("drawing", declared(f'<g style="stroke: currentColor">{flat}</g>')) == []
    mixed = f'<g stroke="color-mix(in srgb, var(--ink-1) 40%, var(--ground))">{flat}</g>'
    assert found("drawing", declared(mixed)) == []


def test_a_figure_that_paints_a_depicted_material_by_hand_is_sent_to_the_kit() -> None:
    assert MATERIAL_PARTS == ("cloth", "bath", "paste", "section", "piece")
    body = rects(6) + '<rect x="100" y="100" width="80" height="80" fill="var(--dye-indigo)"/>'
    assert found("drawing", declared(body)) == [
        "the drawing paints --dye-indigo by hand, which the kit's cloth, bath, paste, section or piece part "
        f"draws textured, framed and named in a key; {KIT_POINTER}"
    ]
    said = {**TEXTS, "u0003": "A section through the mould"}
    assert found("drawing", declared(body), said) == [
        f"the drawing paints --dye-indigo by hand, which the kit's section part draws textured, framed and named in a key; {KIT_POINTER}",
        f"the drawing is said to show section, which the kit's section part draws; {KIT_POINTER}",
    ]


PAINTED_INDIGO = (
    "the drawing paints --dye-indigo by hand, which the kit's cloth, bath, paste, section or piece part draws "
    f"textured, framed and named in a key; {KIT_POINTER}"
)
NO_INK = (
    f"the drawing has no line work in ink: edge what it shows in --ink-1, --ink-2 or --ink-3; {KIT_POINTER}"
)
TONE = '<rect x="100" y="100" width="80" height="80" fill="{}"/>'


def current_colour_rects(colour: str) -> str:
    shapes = rects(6, stroke=' stroke="currentColor"').replace('fill="var(--sunk)"', 'fill="currentColor"')
    return f'<g color="{colour}">{shapes}</g>'


def test_a_material_painted_through_current_color_is_painted_by_hand_and_is_no_ink() -> None:
    assert found("drawing", declared(current_colour_rects("var(--dye-indigo)"))) == [NO_INK, PAINTED_INDIGO]
    assert found("drawing", declared(current_colour_rects("var(--ink-2)"))) == []


def test_a_material_painted_through_a_gradient_a_pattern_or_a_used_shape_is_painted_by_hand() -> None:
    gradient = (
        '<defs><linearGradient id="g"><stop offset="0" stop-color="var(--dye-leuco)"/>'
        '<stop offset="1" style="stop-color: var(--dye-indigo)"/></linearGradient></defs>'
    )
    assert found("drawing", declared(gradient + rects(6) + TONE.format("url(#g)"))) == [
        "the drawing paints --dye-indigo, --dye-leuco by hand, which the kit's cloth, bath, paste, section or "
        f"piece part draws textured, framed and named in a key; {KIT_POINTER}"
    ]
    pattern = (
        '<defs><pattern id="p" width="4" height="4"><path d="M0 0 L4 4" stroke="var(--dye-indigo)"/>'
        "</pattern></defs>"
    )
    assert found("drawing", declared(pattern + rects(6) + TONE.format("url(#p)"))) == [PAINTED_INDIGO]
    kept = '<defs><rect id="r" width="8" height="8" fill="var(--dye-indigo)"/></defs><use href="#r"/>'
    assert found("drawing", declared(kept + rects(6))) == [PAINTED_INDIGO]
    inked = pattern.replace("var(--dye-indigo)", "var(--ink-3)")
    assert found("drawing", declared(inked + rects(6) + TONE.format("url(#p)"))) == []


def test_a_material_stroke_is_painted_by_hand_and_only_an_ink_stroke_is_line_work() -> None:
    assert found("drawing", declared(rects(6, stroke=' stroke="var(--dye-indigo)"'))) == [
        NO_INK,
        PAINTED_INDIGO,
    ]
    assert found("drawing", declared(rects(6, stroke=' stroke="var(--ink-3)"'))) == []


def chart(fill: str) -> dict[str, Any]:
    shapes = [
        {
            "tag": "rect",
            "attrs": {"x": str(8 + 40 * at), "y": "20", "width": "30", "height": "60", "fill": fill},
        }
        for at in range(2)
    ]
    return {
        "form": "drawing",
        "drawing": {"tag": "svg", "attrs": {"viewBox": "0 0 120 100"}, "children": shapes},
    }


def test_a_chart_drawn_by_hand_in_a_depicted_material_is_sent_to_a_declared_diagram() -> None:
    assert found("chart", chart("var(--dye-indigo)")) == [
        "the chart's drawing at drawing paints --dye-indigo by hand, which the kit's cloth, bath, paste, section "
        f"or piece part draws textured, framed and named in a key; {KIT_POINTER}"
    ]
    assert found("chart", chart("var(--chart-series)")) == []
    problems = spec_problems("chart", chart("var(--dye-indigo)"), {})
    assert any(
        problem.startswith("the chart's drawing at drawing paints --dye-indigo by hand")
        for problem in problems
    )


def test_a_map_layer_drawn_in_a_material_is_sent_to_the_kit_and_a_swatch_s_printed_motif_is_its_own() -> None:
    layer = {"setting": "drawing", "drawing": chart("var(--dye-madder)")["drawing"]}
    assert found("map_layer", layer) == [
        "the map_layer's drawing at drawing paints --dye-madder by hand, which the kit's cloth, bath, paste, "
        f"section or piece part draws textured, framed and named in a key; {KIT_POINTER}"
    ]
    fixture = next(fixture for fixture in kind_fixtures() if fixture["kind"] == "swatch_pair")
    printed = copy.deepcopy(fixture["spec"])
    printed["swatches"][0]["motif"][0]["attrs"]["fill"] = "var(--dye-kut)"
    assert found("swatch_pair", printed) == []


def test_a_figure_whose_own_words_name_a_kit_part_is_sent_to_that_part() -> None:
    titled = rects(6) + "<title>Cloth lifted from the vat</title>"
    assert found("drawing", declared(titled)) == [
        f"the drawing is said to show cloth, which the kit's cloth part draws; {KIT_POINTER}",
        f"the drawing is said to show vat, which the kit's bath part draws; {KIT_POINTER}",
    ]


def test_a_player_s_hand_painted_material_is_sent_to_a_kit_scene_textured_or_not() -> None:
    soil = {"tag": "ellipse", "attrs": {**SOIL, "fill": "var(--dye-field-soil)", "stroke": "var(--ink-1)"}}
    painted = (
        "the stage_player's drawing at drawing paints --dye-field-soil by hand, which the kit's cloth, bath, "
        f"paste, section or piece part draws textured, framed and named in a key; {AT_THE_KIT}"
    )
    assert scene_found("stage_player", stage_player([*inked_rects(6), soil])) == [painted]
    pattern = {
        "tag": "defs",
        "children": [
            {
                "tag": "pattern",
                "attrs": {"id": "t", "width": "4", "height": "4"},
                "children": [{"tag": "path", "attrs": {"d": "M0 4 L4 0", "stroke": "var(--ink-1)"}}],
            }
        ],
    }
    twin = {"tag": "ellipse", "attrs": {**SOIL, "fill": "url(#t)"}}
    assert scene_found("stage_player", stage_player([pattern, *inked_rects(6), soil, twin])) == [painted]
    lined = {"tag": "ellipse", "attrs": {**SOIL, "fill": "var(--sunk)", "stroke": "var(--ink-1)"}}
    assert scene_found("stage_player", stage_player([*inked_rects(6), lined])) == []


def test_a_player_s_scene_is_held_to_the_bar_at_delivery_now_players_take_kit_scenes() -> None:
    lone = {"tag": "ellipse", "attrs": {**SOIL, "fill": "var(--sunk)"}}
    held = [
        "the stage_player's drawing at drawing draws 1 shapes, fewer than the 6 a figure at the bar is drawn "
        f"with; {AT_THE_KIT}",
        "the stage_player's drawing at drawing has no line work in ink: edge what it shows in --ink-1, --ink-2 "
        f"or --ink-3; {AT_THE_KIT}",
    ]
    assert found("stage_player", stage_player([lone])) == held
    assert scene_found("stage_player", stage_player([lone])) == held
    assert scene_problems("process_replay", {"steps": [{"drawing": lone}]}, {}) == []


def test_molecule_drawings_are_the_molecule_kit_s_and_icons_are_not_figures() -> None:
    for fixture in kind_fixtures():
        if fixture["kind"] in ("structure_diagram", "molecule_3d"):
            dumped = checked_spec(fixture["kind"], fixture["spec"]).model_dump(mode="json")
            assert drawn_art_problems(fixture["kind"], dumped, {}) == []
    icon = {
        "tag": "svg",
        "attrs": {"viewBox": "0 0 14 14"},
        "children": [{"tag": "path", "attrs": {"d": "M3 2 L12 7 L3 12 Z"}}],
    }
    spec = {"playIcon": icon, "steps": [{"drawing": {"tag": "g", "children": []}}], "scenes": [icon]}
    assert [drawn.where for drawn in free_drawings("process_replay", spec)] == [
        "the process_replay's drawing at steps[0].drawing",
        "the process_replay's drawing at scenes[0]",
    ]


def test_the_delivery_gates_send_a_hand_painted_drawing_to_the_kit() -> None:
    body = rects(6) + '<rect x="100" y="100" width="80" height="80" fill="var(--dye-indigo)"/>'
    problems = spec_problems("drawing", declared(body), UNITS)
    assert any(problem.startswith("the drawing paints --dye-indigo by hand") for problem in problems)


def test_kutch_ajrakh_s_authored_figures_would_be_refused_from_a_contributor_and_are_never_rechecked() -> (
    None
):
    spec = json.loads(
        (MONOGRAPH_SPECS / "kutch-ajrakh__geology__ajrakhpur-borewell-depth.json").read_text(encoding="utf-8")
    )
    problems = drawn_art_problems("diagram", checked_spec("diagram", spec).model_dump(mode="json"), {})
    assert (
        f"the diagram's drawing at drawing is said to show water, which the kit's water part draws; {KIT_POINTER}"
        in problems
    )
    importers = sorted(
        path.relative_to(APP).as_posix()
        for path in APP.rglob("*.py")
        if "drawn_art import" in path.read_text(encoding="utf-8")
    )
    assert importers == ["research/component_specs_general_delivery.py", "research/simulation_art.py"]
