import dataclasses
from pathlib import Path

from app.research.component_specs_general_delivery import DeliveredComponent, DeliveredUnit
from app.research.unit_ids import UNIT_REF
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings
from app.services.page_export_document import page_export

from .generated_parts import ALUM, TEXT_ALUM, component, generated

LABEL = "bagh-print/economics/bagh-counted"


def _tiles(figure: str) -> DeliveredComponent:
    return DeliveredComponent(
        spec={"classes": [], "tiles": [{"figure": figure, "small": "u0002", "caption": "u0003"}]},
        units={
            **({"u0001": DeliveredUnit(text="315")} if figure == "u0001" else {}),
            "u0002": DeliveredUnit(text="units"),
            "u0003": DeliveredUnit(text=TEXT_ALUM, claim_ids=[ALUM]),
        },
    )


def _built(figure: str, tmp_path: Path):
    tiles = dataclasses.replace(
        component(LABEL, monograph=None), kind="stat_tiles", field="ECONOMICS", delivered=_tiles(figure)
    )
    built = assembled_document(generated(components=(tiles,)), Drawings(root=tmp_path))
    assert built is not None
    return built


def test_a_delivered_tile_draws_the_words_of_its_units_on_the_page_and_on_paper(tmp_path: Path) -> None:
    built = _built("u0001", tmp_path)
    (tile,) = built.specs[LABEL]["tiles"]
    assert (tile["figure"], tile["small"]) == ("315", "units")
    assert UNIT_REF.match(tile["caption"]) and tile["caption"] in built.content.units
    figure = next(shown for shown in page_export(built, built.specs).figures() if shown.label == LABEL)
    lines = [line.plain.strip() for line in figure.lines]
    assert "315" in lines and "units" in lines
    assert any(line.startswith(TEXT_ALUM) for line in lines)
    assert not any(UNIT_REF.match(line) for line in lines)


def test_a_tile_whose_figure_is_its_own_words_keeps_them(tmp_path: Path) -> None:
    built = _built("160", tmp_path)
    (tile,) = built.specs[LABEL]["tiles"]
    assert (tile["figure"], tile["small"]) == ("160", "units")
