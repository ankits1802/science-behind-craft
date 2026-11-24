from __future__ import annotations

from collections.abc import Iterator
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, empty
from .blocks import BlockBase
from .citations import Citation
from .component_specs_kit import DeclaredDiagramSpec, kit_label_problems, kit_labels
from .component_specs_plates_parts import UnitRef

__all__ = [
    "KIT_FIGURE_KIND",
    "KIT_LABEL_MAX_CHARS",
    "KitFigureBlock",
    "KitLabel",
    "diagram_refs",
]

KIT_FIGURE_KIND = "kit_figure"
KIT_LABEL_MAX_CHARS = 120


class KitLabel(ContractModel):
    ref: UnitRef
    text: str = Field(min_length=1, max_length=KIT_LABEL_MAX_CHARS)
    citations: list[Citation] = Field(default_factory=list, exclude_if=empty)


class KitFigureBlock(BlockBase):
    kind: Literal["kit_figure"]
    version: Literal[1]
    diagram: DeclaredDiagramSpec
    labels: list[KitLabel] = Field(min_length=1)

    @model_validator(mode="after")
    def _every_unit_named_once_and_every_part_cited(self) -> Self:
        named = [label.ref for label in self.labels]
        if len(set(named)) != len(named):
            raise ValueError(f"kit figure {self.id} names each label once")
        if set(named) != set(diagram_refs(self.diagram)):
            raise ValueError(f"kit figure {self.id} names exactly the labels its diagram draws")
        cited = {label.ref for label in self.labels if label.citations}
        problems = kit_label_problems(self.diagram, cited)
        if problems:
            raise ValueError(f"kit figure {self.id}: {problems[0]}")
        return self

    def citations(self) -> Iterator[Citation]:
        for label in self.labels:
            yield from label.citations

    def shown_labels(self) -> list[str]:
        return [label.text for label in self.labels]


def diagram_refs(diagram: DeclaredDiagramSpec) -> list[str]:
    refs = [diagram.head.title, diagram.head.caption, diagram.alt]
    for panel in diagram.panels:
        refs += [panel.label, panel.text, panel.via]
    refs += [ref for ref, _ in kit_labels(diagram)]
    return list(dict.fromkeys(ref for ref in refs if ref is not None))
