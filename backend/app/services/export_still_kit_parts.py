from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.research.art_kit import EARTH
from app.research.component_specs_kit import BathPart, BlockPart, ClothPart, PastePart, PiecePart, SectionPart

from .export_still_kit_surfaces import (
    INK,
    INK_FAINT,
    INK_SOFT,
    NEUTRAL_LIQUOR,
    PAPER,
    SHADE,
    WELL,
    Node,
    PrintBox,
    line_path,
    material_path,
    motif_tiles,
    paint,
    path,
    rect_d,
    shaded,
    star_points,
)

__all__ = ["bath_nodes", "block_nodes", "cloth_nodes", "paste_nodes", "piece_nodes", "section_nodes"]

SWATCH_BOX: PrintBox = (16, 14, 88, 86)
LENGTH = "M4 32 H116 V86 H4 Z"
LENGTH_BOX: PrintBox = (4, 32, 90, 54)
LENGTH_TURN = "M94 86 L116 64 V86 Z"
FOLDS = "M12 36 H98 C110 36 110 56 98 56 H22 C10 56 10 76 22 76 H98 C110 76 110 96 98 96 H12"
BLOCK_TOP = "M22 30 L36 18 H104 L90 30 Z"
BLOCK_FRONT = "M22 30 H90 V58 H22 Z"
BLOCK_SIDE = "M90 30 L104 18 V46 L90 58 Z"
BLOCK_HANDLE = "M54 22 C54 14 58 6 63 6 C68 6 72 14 72 22 Z"
BLOCK_PRINT_BOX: PrintBox = (14, 72, 92, 36)
PASTE_SLAB = rect_d(10, 66, 100, 36)
PASTE_SPREAD = "M10 66 V50 C22 44 32 54 46 48 C60 42 72 52 86 46 C96 42 104 46 110 48 V66 Z"
PASTE_GROUND_BOX: PrintBox = (14, 14, 92, 92)
PASTE_OUTLINES = ((38, 38), (82, 38), (38, 82), (82, 82))
SECTION_LEFT, SECTION_TOP, SECTION_SIZE = 10.0, 10.0, 100.0


@dataclass(frozen=True)
class Vessel:
    wall: str
    liquor: str
    surface: float
    span: tuple[float, float]
    earth: str | None = None
    rim: tuple[float, float, float, float] | None = None


VESSELS: Mapping[str, Vessel] = MappingProxyType(
    {
        "vat": Vessel(
            wall="M20 40 C20 92 36 114 60 114 C84 114 100 92 100 40 Z",
            liquor="M25 54 C27 92 40 107 60 107 C80 107 93 92 95 54 Z",
            surface=54,
            span=(26, 94),
            earth="M0 40 H120 V120 H0 Z",
            rim=(60, 40, 40, 7),
        ),
        "pot": Vessel(
            wall="M34 34 C16 48 14 88 32 104 C44 114 76 114 88 104 C106 88 104 48 86 34 Z",
            liquor="M21 58 H99 C101 82 96 96 85 103 C74 109 46 109 35 103 C24 96 19 82 21 58 Z",
            surface=58,
            span=(21, 99),
            rim=(60, 34, 27, 5),
        ),
        "trough": Vessel(
            wall="M8 44 H112 L104 106 H16 Z",
            liquor="M12 58 H108 L102.3 100 H17.7 Z",
            surface=58,
            span=(12, 108),
        ),
        "pit": Vessel(
            wall="M22 40 V110 H98 V40 Z",
            liquor="M26 56 H94 V106 H26 Z",
            surface=56,
            span=(26, 94),
            earth="M0 40 H120 V120 H0 Z",
        ),
    }
)


@dataclass(frozen=True)
class Outline:
    faces: tuple[str, ...]
    marks: str | None
    print_box: PrintBox


PIECES: Mapping[str, Outline] = MappingProxyType(
    {
        "lump": Outline(
            (
                "M24 86 C12 72 20 46 40 38 C52 33 62 42 74 37 C92 31 108 48 104 66 C102 80 94 94 72 97 C52 99 32 97 24 86 Z",
            ),
            None,
            (36, 50, 56, 36),
        ),
        "vessel": Outline(
            (
                "M52 12 H68 L66 22 C66 28 78 32 84 44 C92 58 90 78 78 90 C74 94 70 96 68 98 L70 108 H50 L52 98 "
                "C50 96 46 94 42 90 C30 78 28 58 36 44 C42 32 54 28 54 22 Z",
            ),
            "M54 22 H66 M50 98 H70",
            (40, 48, 40, 36),
        ),
        "slab": Outline(
            ("M12 50 H86 V94 H12 Z", "M86 50 L108 32 V76 L86 94 Z", "M12 50 L34 32 H108 L86 50 Z"),
            None,
            (16, 56, 66, 34),
        ),
        "billet": Outline(
            (
                "M20 40 H94 C101 40 106 52 106 66 C106 80 101 92 94 92 H20 Z",
                "M20 40 C13 40 8 52 8 66 C8 80 13 92 20 92 C27 92 32 80 32 66 C32 52 27 40 20 40 Z",
            ),
            "M20 52 C15 52 13 60 13 66 C13 72 15 80 20 80 C25 80 27 72 27 66 C27 60 25 52 20 52 Z",
            (36, 46, 60, 40),
        ),
        "sheet": Outline(
            ("M14 22 H106 V84 L86 104 H14 Z", "M86 104 C88 94 96 86 106 84 Z"), None, (18, 26, 84, 56)
        ),
        "figure": Outline(
            (
                "M54 40 C49 43 45 49 44 58 L38 98 C38 104 43 108 60 108 C77 108 82 104 82 98 L76 58 C75 49 71 43 66 40 Z",
                "M60 12 C67 12 72 17 72 24 C72 31 67 36 60 36 C53 36 48 31 48 24 C48 17 53 12 60 12 Z",
            ),
            "M45 60 C36 66 32 74 31 84 M75 60 C84 66 88 74 89 84",
            (46, 60, 28, 40),
        ),
        "culm": Outline(
            ("M46 6 H74 V114 H46 Z",),
            "M44 38 H76 M44 78 H76 M46 34 C54 40 66 40 74 34 M46 74 C54 80 66 80 74 74",
            (48, 10, 24, 100),
        ),
    }
)


def cloth_nodes(part: ClothPart) -> list[Node]:
    if part.form == "folded":
        return [path(FOLDS, stroke=INK, width="15.4"), path(FOLDS, stroke=paint(part.material), width="13")]
    swatch = part.form == "swatch"
    d = rect_d(*SWATCH_BOX) if swatch else LENGTH
    tiles = None
    if part.printed is not None:
        size = 22 if swatch else 18
        tiles = motif_tiles(
            part.printed.motif, SWATCH_BOX if swatch else LENGTH_BOX, part.printed.material, size
        )
    nodes = material_path(d, part.material, tiles=tiles)
    if swatch:
        return [*nodes, *(path(f"M{18 + at * 4} 100 V106", stroke=INK_SOFT, width="1") for at in range(22))]
    turn = path(LENGTH_TURN, fill=shaded(part.material, 78), stroke=INK, width="1.2")
    return [*nodes, turn, path("M4 38 H112", stroke=INK_SOFT, width=".8")]


def block_nodes(part: BlockPart) -> list[Node]:
    colour = part.paste or "--ink-2"
    printed = rect_d(*BLOCK_PRINT_BOX)
    return [
        *line_path(BLOCK_SIDE, fill=SHADE),
        *line_path(BLOCK_FRONT, fill=SHADE),
        *line_path(BLOCK_TOP),
        *line_path(BLOCK_HANDLE),
        path("M22 58 H90", stroke=INK, width="2.2"),
        path(printed, fill=PAPER),
        *motif_tiles(part.motif, BLOCK_PRINT_BOX, colour, 16),
        path(printed, stroke=INK_SOFT, width="1"),
        path("M56 62 V68 M60 64 L56 68 L52 64", stroke=INK_SOFT, width="1.2"),
    ]


def bath_nodes(part: BathPart) -> list[Node]:
    vessel = VESSELS[part.vessel]
    nodes = [path(vessel.earth, fill=WELL)] if vessel.earth else []
    nodes += line_path(vessel.wall)
    if part.liquor:
        nodes += material_path(vessel.liquor, part.liquor, edge=INK_SOFT)
    else:
        nodes.append(path(vessel.liquor, fill=NEUTRAL_LIQUOR))
    nodes.append(
        path(f"M{vessel.span[0]:g} {vessel.surface:g} H{vessel.span[1]:g}", stroke=INK_SOFT, width="1")
    )
    if vessel.rim:
        cx, cy, rx, ry = vessel.rim
        rim = {"cx": f"{cx:g}", "cy": f"{cy:g}", "rx": f"{rx:g}", "ry": f"{ry:g}"}
        nodes.append(
            {"tag": "ellipse", "attrs": {**rim, "fill": "none", "stroke": INK, "stroke-width": "1.4"}}
        )
    if vessel.earth:
        nodes.append(path("M0 40 H120", stroke=INK, width="1.6"))
    return nodes + _bath_piece(part, vessel)


def _bath_piece(part: BathPart, vessel: Vessel) -> list[Node]:
    if part.piece is None:
        return []
    bottom = vessel.surface + 34
    soaked = path(
        f"M52 {vessel.surface:g} H68 V{bottom:g} H52 Z",
        fill=paint(part.liquor) if part.liquor else NEUTRAL_LIQUOR,
    )
    soaked["attrs"]["fill-opacity"] = ".45"
    return [
        *material_path(f"M52 22 H68 V{bottom:g} H52 Z", part.piece),
        soaked,
        path("M30 22 H90", stroke=INK, width="2.4"),
    ]


def paste_nodes(part: PastePart) -> list[Node]:
    rest = part.dried or part.material
    spread = part.form == "spread"
    ground_d = PASTE_SLAB if spread else rect_d(*PASTE_GROUND_BOX)
    if part.on:
        nodes = material_path(ground_d, part.on)
    else:
        nodes = [path(ground_d, fill=PAPER, stroke=INK, width="1.2")]
    if spread:
        return nodes + material_path(PASTE_SPREAD, rest)
    if part.form == "printed":
        return nodes + motif_tiles("dots", PASTE_GROUND_BOX, rest, 20)
    outlines = [
        {
            "tag": "polygon",
            "attrs": {
                "points": star_points(cx, cy, 17, 7.5),
                "fill": "none",
                "stroke": paint(rest),
                "stroke-width": "5",
            },
        }
        for cx, cy in PASTE_OUTLINES
    ]
    return nodes + outlines


def section_nodes(part: SectionPart) -> list[Node]:
    height = SECTION_SIZE / len(part.layers)
    nodes: list[Node] = []
    for at, layer in enumerate(part.layers):
        band = rect_d(SECTION_LEFT, SECTION_TOP + height * at, SECTION_SIZE, height)
        nodes += (
            [path(band, fill=WELL)]
            if layer.material == EARTH
            else material_path(band, layer.material, edge=None)
        )
    seams = " ".join(
        f"M{SECTION_LEFT:g} {SECTION_TOP + height * at:.2f} H{SECTION_LEFT + SECTION_SIZE:g}"
        for at in range(1, len(part.layers))
    )
    if seams:
        nodes.append(path(seams, stroke=INK, width=".8"))
    nodes.append(path(rect_d(SECTION_LEFT, SECTION_TOP, SECTION_SIZE, SECTION_SIZE), stroke=INK, width="1.2"))
    nodes.append(
        path(
            f"M{SECTION_LEFT - 4:g} {SECTION_TOP:g} H{SECTION_LEFT + SECTION_SIZE + 4:g}",
            stroke=INK,
            width="1.6",
        )
    )
    return nodes


def piece_nodes(part: PiecePart) -> list[Node]:
    outline = PIECES[part.shape]
    nodes: list[Node] = []
    for at, face in enumerate(outline.faces):
        nodes += _face(face, part.material, at)
    if part.inlay is not None:
        nodes += motif_tiles(part.inlay.motif, outline.print_box, part.inlay.material, 14)
        nodes.append(path(outline.faces[0], stroke=INK, width="1.2"))
    if outline.marks:
        nodes.append(path(outline.marks, stroke=INK if part.material else INK_FAINT, width="1.1"))
    return nodes


def _face(d: str, material: str | None, at: int) -> list[Node]:
    if material is None:
        return line_path(d)
    if at == 0:
        return material_path(d, material)
    return [path(d, fill=shaded(material, 82 if at == 1 else 92)), path(d, stroke=INK, width="1.2")]
