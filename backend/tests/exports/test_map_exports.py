from typing import Any

from app.geo.map_base import site_point
from app.research.datasets import BOUNDARY_CAPTION
from app.services.export_map_base import MAP_PRINT_PIXELS
from app.services.export_still_png import still_png
from app.services.export_stills import Colour, Still, token_colour
from app.services.page_export_document import page_export
from app.services.page_export_docx import STILL_WIDTH_MM
from app.services.page_export_model import ExportFigure

from .page_fixture import fixture_page

PLACES = "bidriware/history/centres"
CODED = "bidriware/chemistry/patina-bath-figure"
MM_PER_INCH = 25.4
PRINT_DPI = 300
JAIPUR = 102


def _colour(token: str) -> Colour:
    found = token_colour(token)
    assert found is not None, token
    return found


def _lines(still: Still) -> set[Colour]:
    return {path.line for path in still.paths if path.line is not None}


def _fills(still: Still) -> set[Colour]:
    return {path.fill for path in still.paths if path.fill is not None}


def _figure(names: tuple[str, ...], label: str, spec: dict[str, Any] | None = None) -> ExportFigure:
    page = fixture_page(names)
    specs = {**page.specs, label: spec} if spec is not None else page.specs
    return next(shown for shown in page_export(page, specs).figures() if shown.label == label)


def _coded_box_spec(box: tuple[float, float, float, float], *, mapped: bool) -> dict[str, Any]:
    page = fixture_page(("coded_figure",))
    west, south, east, north = box
    corner, far = site_point(west, north), site_point(east, south)
    view = " ".join(
        f"{value:.1f}" for value in (corner[0], corner[1], far[0] - corner[0], far[1] - corner[1])
    )
    flag = ' data-map=""' if mapped else ""
    dot = f'<circle cx="{corner[0] + 5:.1f}" cy="{corner[1] + 5:.1f}" r="1" fill="var(--madder)"/>'
    spec = {**page.specs[CODED], "code": f'<svg viewBox="{view}"{flag}>{dot}</svg>'}
    return {**spec, "map": {"layers": ["relief", "rivers"], "districts": [JAIPUR]}} if mapped else spec


def test_a_places_map_exports_on_the_site_s_base_with_its_numbered_pins_credits_and_boundary_note() -> None:
    figure = _figure(("map_layer",), PLACES)
    (still,) = figure.stills
    assert still.pixels == MAP_PRINT_PIXELS
    assert _colour("--elevation-1") in _fills(still)
    for token in ("--map-border-state", "--map-river", "--map-border-intl"):
        assert _colour(token) in _lines(still), token
    assert [text.text for text in still.texts] == ["1", "2", "3", "4", "5"]
    assert BOUNDARY_CAPTION in [line.plain for line in figure.lines]
    assert any("ETOPO1" in credit for credit in figure.credits)
    assert any("Natural Earth" in credit for credit in figure.credits)
    assert any(line.plain.startswith("1. ") for line in figure.lines)


def test_a_coded_map_exports_on_the_site_s_base_under_its_own_drawing() -> None:
    figure = _figure(("coded_figure",), CODED, _coded_box_spec((76.8, 28.35, 77.6, 28.95), mapped=True))
    (still,) = figure.stills
    assert still.pixels == MAP_PRINT_PIXELS
    for token in ("--map-border-state", "--map-border-district", "--map-river"):
        assert _colour(token) in _lines(still), token
    assert still.paths[-1].fill == _colour("--madder")
    assert _colour("--elevation-1") in _fills(still)
    assert BOUNDARY_CAPTION in [line.plain for line in figure.lines]
    assert any("Indian district boundaries" in credit for credit in figure.credits)


def test_a_coded_still_that_is_not_its_map_exports_without_the_base() -> None:
    figure = _figure(("coded_figure",), CODED, _coded_box_spec((76.8, 28.35, 77.6, 28.95), mapped=False))
    (still,) = figure.stills
    assert still.pixels is None
    assert [path.fill for path in still.paths] == [_colour("--madder")]
    assert BOUNDARY_CAPTION not in [line.plain for line in figure.lines]
    assert figure.credits == ()


def test_a_map_still_prints_at_300_dots_an_inch_across_the_word_figure() -> None:
    (still,) = _figure(("map_layer",), PLACES).stills
    picture = still_png(still, pixels=still.pixels or 0)
    assert picture is not None
    assert max(picture.width, picture.height) == MAP_PRINT_PIXELS
    assert MAP_PRINT_PIXELS / (STILL_WIDTH_MM / MM_PER_INCH) >= PRINT_DPI
