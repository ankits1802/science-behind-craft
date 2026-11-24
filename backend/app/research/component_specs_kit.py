from __future__ import annotations

from collections.abc import Collection, Iterator
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from .art_kit import (
    CLOTH_FORMS,
    HEAT_SOURCES,
    KIT_MOTIONS,
    LAYERS_MAX,
    LAYERS_MIN,
    LAYOUTS,
    MOTIFS,
    PANELS_PER_LAYOUT,
    PARTS_PER_PANEL_MAX,
    PASTE_FORMS,
    PIECE_SHAPES,
    TOOLS,
    VESSELS,
    WATER_FORMS,
)
from .base import ContractModel, absent
from .component_specs_general import GeneralHead
from .component_specs_plates_parts import UnitRef
from .drawing_roles import MATERIAL_ROLES

__all__ = [
    "KIT_DIAGRAM",
    "BathPart",
    "BlockPart",
    "ClothPart",
    "DeclaredDiagramSpec",
    "HeatPart",
    "KitPanel",
    "KitPrint",
    "PastePart",
    "PiecePart",
    "SectionLayer",
    "SectionPart",
    "ToolPart",
    "WaterPart",
    "kit_label_problems",
    "kit_labels",
]

KIT_DIAGRAM = "diagram"
TOKEN_PREFIX = "--"
NOT_RECORDED = (
    "{token} is not a depicted material the design system records: a kit part takes a --dye-* or --dip-* "
    "material by its token, and a material no record holds is asked for first"
)
UNCITED = (
    "the unit {ref}, the label of {where}, cites no fact: a kit part's label rests on the facts that state it"
)
MOTION_NEEDS = {
    "dip": ("bath", "a bath part with a piece in it"),
    "take": ("cloth", "a cloth part"),
    "dry": ("paste", "a paste part that names what it dries to"),
}


def _material(token: str) -> str:
    if not token.startswith(TOKEN_PREFIX) or token.removeprefix(TOKEN_PREFIX) not in MATERIAL_ROLES:
        raise ValueError(NOT_RECORDED.format(token=token))
    return token


Material = Annotated[str, AfterValidator(_material)]
Motif = Literal[*MOTIFS]


class KitPrint(ContractModel):
    motif: Motif
    material: Material


class ClothPart(ContractModel):
    part: Literal["cloth"]
    form: Literal[*CLOTH_FORMS]
    material: Material
    printed: KitPrint | None = Field(default=None, exclude_if=absent)
    label: UnitRef


class BlockPart(ContractModel):
    part: Literal["block"]
    motif: Motif
    paste: Material | None = Field(default=None, exclude_if=absent)
    label: UnitRef


class BathPart(ContractModel):
    part: Literal["bath"]
    vessel: Literal[*VESSELS]
    liquor: Material | None = Field(default=None, exclude_if=absent)
    piece: Material | None = Field(default=None, exclude_if=absent)
    label: UnitRef


class PastePart(ContractModel):
    part: Literal["paste"]
    form: Literal[*PASTE_FORMS]
    material: Material
    on: Material | None = Field(default=None, exclude_if=absent)
    dried: Material | None = Field(default=None, exclude_if=absent)
    label: UnitRef


class HeatPart(ContractModel):
    part: Literal["heat"]
    source: Literal[*HEAT_SOURCES]
    label: UnitRef


class WaterPart(ContractModel):
    part: Literal["water"]
    form: Literal[*WATER_FORMS]
    label: UnitRef


class ToolPart(ContractModel):
    part: Literal["tool"]
    tool: Literal[*TOOLS]
    held: bool = True
    load: Material | None = Field(default=None, exclude_if=absent)
    label: UnitRef


class SectionLayer(ContractModel):
    material: Material | Literal["earth"]
    label: UnitRef


class SectionPart(ContractModel):
    part: Literal["section"]
    layers: list[SectionLayer] = Field(min_length=LAYERS_MIN, max_length=LAYERS_MAX)
    label: UnitRef


class PiecePart(ContractModel):
    part: Literal["piece"]
    shape: Literal[*PIECE_SHAPES]
    material: Material | None = Field(default=None, exclude_if=absent)
    inlay: KitPrint | None = Field(default=None, exclude_if=absent)
    label: UnitRef


KitPartSpec = Annotated[
    ClothPart | BlockPart | BathPart | PastePart | HeatPart | WaterPart | ToolPart | SectionPart | PiecePart,
    Field(discriminator="part"),
]


class KitPanel(ContractModel):
    label: UnitRef
    text: UnitRef | None = Field(default=None, exclude_if=absent)
    via: UnitRef | None = Field(default=None, exclude_if=absent)
    motion: Literal[*KIT_MOTIONS] | None = Field(default=None, exclude_if=absent)
    parts: list[KitPartSpec] = Field(min_length=1, max_length=PARTS_PER_PANEL_MAX)

    @model_validator(mode="after")
    def _motion_explains_a_part(self) -> Self:
        if self.motion is None:
            return self
        name, needs = MOTION_NEEDS[self.motion]
        if not any(_moves(part, name) for part in self.parts):
            raise ValueError(f"the {self.motion} motion explains {needs}, which this panel does not hold")
        return self


class DeclaredDiagramSpec(ContractModel):
    head: GeneralHead
    layout: Literal[*LAYOUTS]
    alt: UnitRef
    panels: list[KitPanel] = Field(min_length=1, max_length=PANELS_PER_LAYOUT["steps"][1])

    @model_validator(mode="after")
    def _laid_out(self) -> Self:
        low, high = PANELS_PER_LAYOUT[self.layout]
        if not low <= len(self.panels) <= high:
            raise ValueError(
                f"a {self.layout} diagram has {_count(low, high)} panels, not {len(self.panels)}"
            )
        if self.layout == "section" and [part.part for part in self.panels[0].parts] != ["section"]:
            raise ValueError("a section diagram's one panel holds one section part and nothing else")
        arrows = self.layout in ("sequence", "before_after")
        if any(panel.via is not None for panel in self.panels[: 1 if arrows else None]):
            raise ValueError(
                "only a sequence or a before and after names a change, on the arrow into a later panel"
            )
        return self


def kit_labels(spec: DeclaredDiagramSpec) -> Iterator[tuple[str, str]]:
    for at, panel in enumerate(spec.panels, start=1):
        for part in panel.parts:
            yield part.label, f"panel {at}'s {part.part} part"
            if isinstance(part, SectionPart):
                for depth, layer in enumerate(part.layers, start=1):
                    yield layer.label, f"layer {depth} of panel {at}'s section"


def kit_label_problems(spec: DeclaredDiagramSpec, cited: Collection[str]) -> list[str]:
    return [UNCITED.format(ref=ref, where=where) for ref, where in kit_labels(spec) if ref not in cited]


def _moves(part: object, name: str) -> bool:
    if name == "bath":
        return isinstance(part, BathPart) and part.piece is not None
    if name == "paste":
        return isinstance(part, PastePart) and part.dried is not None
    return isinstance(part, ClothPart)


def _count(low: int, high: int) -> str:
    return str(low) if low == high else f"{low} to {high}"
