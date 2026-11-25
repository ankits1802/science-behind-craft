from __future__ import annotations

import math
from collections.abc import Sequence

from app.research.component_specs_kit import SpeciesPart

from .export_still_kit_surfaces import INK, INK_SOFT, PAPER, Node, group, material_path, path

__all__ = ["BEAD", "REACTION_ARROW", "species_boxes", "species_nodes", "species_scene_nodes"]

PART_BOX = 120.0
BEAD = "M14 60 A46 46 0 1 0 106 60 A46 46 0 1 0 14 60 Z"
CRACK = "M60 14 L51 40 L66 58 L52 80 L60 106"
ARRIVAL = "M60 1 V11 M54 5 L60 11 L66 5"
REACTION_ARROW = "M110 80 H129 M123 74 L130 80 L123 86"
UNRECORDED_DASH = "6 4"
PRODUCT, REAGENT = "product", "reagent"
FRAME_TOP, FRAME_HEIGHT = 4.0, 152.0
COLUMN_WIDTH = 104.0
COLUMNS = (0.0, 136.0)
GAP = 8.0
ONE_ACROSS_MOST = 2
BEAD_MOST, PAIRED_MOST = 96.0, 48.0
Box = tuple[float, float, float]


def species_nodes(part: SpeciesPart) -> list[Node]:
    if part.material is not None:
        nodes = material_path(BEAD, part.material)
    else:
        bead = path(BEAD, fill=PAPER, stroke=INK_SOFT, width="1.4")
        bead["attrs"]["stroke-dasharray"] = UNRECORDED_DASH
        nodes = [bead]
    if part.breaks:
        nodes += [path(CRACK, stroke=PAPER, width="5"), path(CRACK, stroke=INK, width="1.4")]
    if part.role == REAGENT:
        nodes.append(path(ARRIVAL, stroke=INK_SOFT, width="1.6"))
    return nodes


def species_boxes(parts: Sequence[SpeciesPart]) -> list[Box]:
    reactants = [at for at, part in enumerate(parts) if part.role != PRODUCT]
    products = [at for at, part in enumerate(parts) if part.role == PRODUCT]
    boxes: dict[int, Box] = {}
    for column, side in zip(COLUMNS, (reactants, products), strict=True):
        for at, box in zip(side, _column(column, len(side)), strict=True):
            boxes[at] = box
    return [boxes[at] for at in range(len(parts))]


def species_scene_nodes(parts: Sequence[SpeciesPart]) -> list[Node]:
    placed = [
        group(species_nodes(part), f"translate({x:g} {y:g}) scale({size / PART_BOX:.4f})")
        for part, (x, y, size) in zip(parts, species_boxes(parts), strict=True)
    ]
    return [*placed, path(REACTION_ARROW, stroke=INK, width="1.6")]


def _column(left: float, count: int) -> list[Box]:
    if count == 0:
        return []
    across = 1 if count <= ONE_ACROSS_MOST else 2
    rows = math.ceil(count / across)
    most = BEAD_MOST if across == 1 else PAIRED_MOST
    size = min(most, (FRAME_HEIGHT - GAP * (rows - 1)) / rows)
    width = across * size + GAP * (across - 1)
    height = rows * size + GAP * (rows - 1)
    x0 = left + (COLUMN_WIDTH - width) / 2
    y0 = FRAME_TOP + (FRAME_HEIGHT - height) / 2
    return [
        (
            round(x0 + (at % across) * (size + GAP), 2),
            round(y0 + (at // across) * (size + GAP), 2),
            round(size, 2),
        )
        for at in range(count)
    ]
