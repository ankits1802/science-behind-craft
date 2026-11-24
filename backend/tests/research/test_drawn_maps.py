import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.data.kind_fixture_files import kind_fixtures
from app.research.component_specs import MAP_POINTER, checked_spec
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.research.drawn_maps import drawn_map_problems

MONOGRAPH_SPECS = (
    Path(__file__).resolve().parents[2] / "app" / "data" / "monographs" / "Kutch-Ajrakh" / "specs"
)
HAND_DRAWN = (
    "kutch-ajrakh__geography__suran-flowing-north-map.json",
    "kutch-ajrakh__history__dhamadka-to-ajrakhpur-move-map.json",
    "kutch-ajrakh__geology__dhamadka-epicentre-circle-map.json",
)
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240">{}</svg>'
UNITS = {
    "u0001": DeliveredUnit(text="A drawing"),
    "u0002": DeliveredUnit(
        text="What the drawing shows.", claim_ids=[uuid.UUID("5d4a7f0e-6a1e-4c1b-9b8e-2f7d3c9a1b20")]
    ),
}


def outline(points: int) -> str:
    steps = " ".join(f"L{10 + step * 3} {20 + (step % 7) * 4}" for step in range(points - 1))
    return f'<path d="M10 20 {steps} Z" fill="none" stroke="var(--ink-1)"/>'


def dots(count: int, paint: str) -> str:
    return "".join(f'<circle cx="{40 + 30 * n}" cy="120" r="5" fill="var({paint})"/>' for n in range(count))


def drawing(body: str) -> dict[str, Any]:
    return {"head": {"title": "u0001"}, "svg": SVG.format(body), "alt": "u0002"}


def refused(body: str) -> list[str]:
    return drawn_map_problems("drawing", checked_spec("drawing", drawing(body)).model_dump(mode="json"))


@pytest.mark.parametrize("name", HAND_DRAWN)
def test_kutch_ajrakh_s_hand_drawn_maps_would_be_refused_from_a_contributor(name: str) -> None:
    spec = checked_spec("map_layer", json.loads((MONOGRAPH_SPECS / name).read_text(encoding="utf-8")))
    (problem,) = drawn_map_problems("map_layer", spec.model_dump(mode="json"))
    assert problem == (
        f"the map_layer draws a map by hand: it draws with the page kit's map frame and pins; {MAP_POINTER}"
    )


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ('<path d="M10 10 L300 10 L300 200 Z" fill="var(--map-land)"/>', "it paints the base map's land"),
        ('<path d="M10 10 L300 10" stroke="var(--map-border-state)"/>', "it paints the base map's land"),
        (dots(2, "--terracotta"), "it marks 2 places as dots in the place colours"),
        (
            f'<g fill="var(--map-marker)">{dots(3, "--map-marker").replace(" fill=", " data-x=")}</g>',
            "marks 3 places",
        ),
        (outline(60) + dots(2, "--ink-2"), "it draws an outline of 60 points with 2 dots on it"),
        (
            '<g class="pin" data-pin="Sanganer"><circle r="4" fill="var(--ink-1)"/></g>',
            "the page kit's map frame",
        ),
    ],
)
def test_a_drawing_that_is_a_map_of_places_is_refused_with_the_pointer(body: str, reason: str) -> None:
    (problem,) = refused(body)
    assert problem.startswith("the drawing draws a map by hand: ") and reason in problem
    assert problem.endswith(MAP_POINTER)


@pytest.mark.parametrize(
    "body",
    [
        dots(1, "--terracotta"),
        outline(59) + dots(2, "--ink-2"),
        outline(80) + dots(1, "--ink-2"),
        '<rect x="20" y="20" width="280" height="200" fill="var(--sunk)"/>' + dots(4, "--dye-indigo"),
        f'<g fill="var(--terracotta)">{dots(3, "--ink-1")}</g>',
        '<path d="M10 200 L310 200" stroke="var(--map-river)"/><rect x="10" y="200" width="300" height="30" fill="var(--map-water)"/>',
    ],
)
def test_a_drawing_of_a_mechanism_a_section_or_a_vat_is_not_a_map(body: str) -> None:
    assert refused(body) == []


def test_the_delivery_gates_refuse_a_hand_drawn_map_and_keep_the_fixtures() -> None:
    problems = spec_problems("drawing", drawing(dots(3, "--terracotta")), UNITS)
    assert problems[0] == (
        f"the drawing draws a map by hand: it marks 3 places as dots in the place colours; {MAP_POINTER}"
    )
    for fixture in kind_fixtures():
        dumped = checked_spec(fixture["kind"], fixture["spec"]).model_dump(mode="json")
        assert drawn_map_problems(fixture["kind"], dumped) == [], fixture["label"]
