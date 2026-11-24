from io import BytesIO

import pytest
from pypdf import PdfReader

from app.research.component_specs_kit import BathPart, ClothPart, DeclaredDiagramSpec, KitPrint
from app.research.component_specs_science_geometry import MoleculeGeometry
from app.services.export_pdf_kit import kit_figure_pdf
from app.services.export_pdf_still import draw_still
from app.services.export_still_figures import molecule_still, swatch_strip, turned_atoms
from app.services.export_still_kit import diagram_still, kit_scene_parts, part_still, scene_still
from app.services.export_still_map import MapAsk, MapPin, timeline_still
from app.services.export_still_paint import paint_colour, parsed_transform
from app.services.export_still_paths import path_subpaths, points_list
from app.services.export_still_png import still_png
from app.services.export_still_svg import svg_still
from app.services.page_export_units import PageTexts
from app.services.pdf_writer import PdfWriter

from ..learning.figure_fixtures import drawn
from .page_fixture import FIXTURE_LABELS, fixture_page


def line_ops(data: bytes) -> int:
    streams = (page.get_contents() for page in PdfReader(BytesIO(data)).pages)
    return sum(stream.get_data().count(b" l") for stream in streams if stream is not None)


def test_an_answer_s_kit_figure_goes_through_the_page_s_still_renderer() -> None:
    page = fixture_page()
    spec = DeclaredDiagramSpec.model_validate(page.specs[FIXTURE_LABELS["diagram_kit"]])
    texts = PageTexts(page.content)
    text, data = drawn(lambda writer: kit_figure_pdf(writer, spec, lambda ref: texts.plain(ref) or None))
    assert "From zinc-white to black" in text and "1. Sanded level" in text and "2. In the bath" in text
    assert "dipped" in text and "Drawn: Zinc-white alloy, inlaid with silver" in text
    assert line_ops(data) > 500


INDIGO = (0x25, 0x30, 0x45)
MADDER = (0x7E, 0x03, 0x2C)
CLOTH = (0xF4, 0xF2, 0xEA)
INK_1 = (0x1C, 0x18, 0x15)
INK_2 = (0x3A, 0x34, 0x30)
BIDRI_WHITE = (0xD6, 0xD5, 0xCE)
TERRACOTTA = (0xB0, 0x5A, 0x36)
ATOM_O = (0xC3, 0x47, 0x28)


def test_a_path_draws_its_straight_and_relative_commands() -> None:
    [square] = path_subpaths("m10 10 h20 v20 h-20 z")
    assert square.points == ((10, 10), (30, 10), (30, 30), (10, 30)) and square.closed
    first, second = path_subpaths("M0 0 L10 0 M20 0 L30 0")
    assert (first.points, first.closed, second.points) == (((0, 0), (10, 0)), False, ((20, 0), (30, 0)))
    assert points_list("0,0 10,0 10,10") == ((0, 0), (10, 0), (10, 10))


def test_a_curve_and_an_arc_pass_through_the_points_their_geometry_gives() -> None:
    [curve] = path_subpaths("M0 0 C0 10 10 10 10 0")
    assert len(curve.points) == 13 and curve.points[-1] == pytest.approx((10, 0))
    assert curve.points[6] == pytest.approx((5, 7.5))
    [arc] = path_subpaths("M0 0 A10 10 0 0 1 20 0")
    assert arc.points[6] == pytest.approx((10, -10)) and arc.points[-1] == pytest.approx((20, 0))


def test_transforms_and_paints_resolve_as_svg_and_the_design_tokens_say() -> None:
    assert parsed_transform("translate(10 20) scale(2)").apply((1, 1)) == (12, 22)
    assert parsed_transform("rotate(90)").apply((1, 0)) == pytest.approx((0, 1))
    assert paint_colour("var(--dye-indigo)", {}) == (INDIGO, 1.0)
    assert paint_colour("color-mix(in srgb, var(--ink-1) 50%, white)", {}) == ((142, 140, 138), 1.0)
    assert paint_colour("url(#weave)", {}) == (None, 1.0)
    assert paint_colour("#12345", {}) == (None, 1.0)


def test_a_drawing_is_drawn_in_its_view_box_with_its_text_and_without_its_textures() -> None:
    drawing = {
        "tag": "svg",
        "attrs": {"viewBox": "10 10 100 50"},
        "children": [
            {"tag": "defs", "children": [{"tag": "rect", "attrs": {"width": "5", "height": "5"}}]},
            {
                "tag": "rect",
                "attrs": {"x": "10", "y": "10", "width": "20", "height": "10", "fill": "var(--dye-indigo)"},
            },
            {
                "tag": "rect",
                "attrs": {"x": "10", "y": "10", "width": "20", "height": "10", "fill": "url(#weave)"},
            },
            {"tag": "circle", "attrs": {"cx": "50", "cy": "30", "r": "4", "display": "none"}},
            {
                "tag": "text",
                "attrs": {
                    "x": "50",
                    "y": "44",
                    "text-anchor": "middle",
                    "font-size": "12",
                    "fill": "var(--ink-1)",
                },
                "children": ["N"],
            },
        ],
    }
    still = svg_still(drawing)
    assert (still.width, still.height) == (100, 50)
    [rect] = still.paths
    assert rect.points == ((0, 0), (20, 0), (20, 10), (0, 10)) and rect.fill == INDIGO and rect.line is None
    [label] = still.texts
    assert (label.at, label.text, label.size, label.colour, label.anchor) == (
        (40, 34),
        "N",
        12,
        INK_1,
        "middle",
    )


def test_a_kit_cloth_is_drawn_in_its_depicted_material_with_its_printed_motif() -> None:
    cloth = ClothPart(
        part="cloth",
        form="swatch",
        material="--dye-indigo",
        printed=KitPrint(motif="dots", material="--dye-madder"),
        label="u0001",
    )
    still = part_still(cloth)
    assert (still.width, still.height) == (120, 120)
    assert still.paths[0].fill == INDIGO and still.paths[0].points == (
        (16, 14),
        (104, 14),
        (104, 100),
        (16, 100),
    )
    assert sum(path.fill == MADDER for path in still.paths) == 24
    assert len(still.paths) == 1 + 24 + 1 + 22


def test_a_kit_bath_holds_its_liquor_and_the_piece_dipped_in_it() -> None:
    bath = BathPart(part="bath", vessel="vat", liquor="--dye-indigo", piece="--dye-cloth", label="u0001")
    fills = [path.fill for path in part_still(bath).paths]
    assert INDIGO in fills and CLOTH in fills
    assert (157, 162, 171) in fills


def test_a_composed_diagram_draws_its_panels_numbered_with_arrows_between() -> None:
    spec = DeclaredDiagramSpec.model_validate(fixture_page().specs[FIXTURE_LABELS["diagram_kit"]])
    still = diagram_still(spec)
    assert (still.width, still.height) == (800, 160)
    assert [(text.text, text.at) for text in still.texts] == [
        ("1", (4, 14)),
        ("2", (284, 14)),
        ("3", (564, 14)),
    ]
    arrows = [path for path in still.paths if path.line == INK_1 and path.width == 2 and not path.closed]
    assert len(arrows) == 4


def test_a_kit_scene_is_read_from_its_parts_and_drawn_by_the_same_renderer() -> None:
    parts = kit_scene_parts({"parts": [{"part": "heat", "source": "sun", "label": "u0001"}]})
    assert parts is not None and kit_scene_parts({"tag": "svg"}) is None
    still = scene_still(parts)
    assert (still.width, still.height) == (240, 160) and still.drawn


def test_a_molecule_is_drawn_from_its_conformer_as_it_rests() -> None:
    water = MoleculeGeometry(
        atoms=[("O", 0, 0, 0), ("H", 1, 0, 0), ("H", -1, 0, 0)], bonds=[(0, 1, 1), (0, 2, 1)], radius=1
    )
    assert turned_atoms(water, 90, 0)[1] == pytest.approx((0, 0, -1))
    still = molecule_still(water, 0, 0)
    bonds, atoms = still.paths[:2], still.paths[2:]
    assert [bond.line for bond in bonds] == [INK_2, INK_2] and bonds[0].points[0] == pytest.approx((120, 120))
    scale = 208 / 2.68
    assert bonds[0].points[1] == pytest.approx((120 + scale, 120))
    oxygen = atoms[0]
    assert oxygen.fill == ATOM_O
    assert max(x for x, _ in oxygen.points) == pytest.approx(120 + 0.34 * scale)


def test_a_swatch_strip_draws_each_colour_and_an_undepicted_one_in_line_work() -> None:
    still = swatch_strip(["--dye-bidri-white", None])
    assert [(path.fill, path.line) for path in still.paths] == [(BIDRI_WHITE, INK_1), (None, INK_1)]
    assert [text.text for text in still.texts] == ["1", "2"] and still.width == 90


def test_a_timeline_map_pins_every_place_and_hatches_the_home_district() -> None:
    pins = [MapPin(77.144, 17.766, 1), MapPin(78.453, 17.379, 2)]
    still = timeline_still(MapAsk(pins=pins, routes=[(0, 1)], districts=[529, 507], homes=[529]))
    assert [text.text for text in still.texts] == ["1", "2"]
    assert any(path.fill == TERRACOTTA for path in still.paths)
    assert sum(not path.closed and len(path.points) == 2 for path in still.paths) == 1
    lone = timeline_still(MapAsk(pins=[MapPin(31.2375, 30.005, 1)], routes=[], districts=[], homes=[]))
    assert lone.drawn and lone.width > 0


def test_one_still_draws_in_the_pdf_and_rasterises_for_word() -> None:
    spec = DeclaredDiagramSpec.model_validate(fixture_page().specs[FIXTURE_LABELS["diagram_kit"]])
    still = diagram_still(spec)
    picture = still_png(still)
    assert (
        picture is not None
        and picture.data.startswith(b"\x89PNG")
        and (picture.width, picture.height) == (1000, 200)
    )
    writer = PdfWriter("en", orientation="portrait", title="Still")
    writer.new_page()
    assert draw_still(writer, still)
    data = writer.output()
    streams = (page.get_contents() for page in PdfReader(BytesIO(data)).pages)
    assert sum(stream.get_data().count(b" l") for stream in streams if stream is not None) > 500
