from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .component_specs_plates_parts import ClassName, ComponentLabel, DomId, HeldText, UnitRef

__all__ = [
    "LINE_TAGS",
    "ComponentLabel",
    "CssLength",
    "FigureHead",
    "FigureNumber",
    "Placed",
    "TextLine",
    "ToggleGroup",
    "ToggleOption",
]

LINE_TAGS = ("p", "h3", "li", "span", "dt", "dd", "figcaption", "td", "th")
FIGURE_REF_PATTERN = r"^[a-z0-9]+:\d+$"
CSS_LENGTH_PATTERN = r"^-?\d+(\.\d+)?(%|px)?$"

CssLength = Annotated[str, Field(pattern=CSS_LENGTH_PATTERN)]


class TextLine(ContractModel):
    tag: Literal[*LINE_TAGS] = "p"
    classes: list[ClassName] = Field(default_factory=list)
    unit: UnitRef | None = None
    text: HeldText | None = None

    @model_validator(mode="after")
    def _a_unit_or_held_text(self) -> Self:
        if self.unit is not None and self.text is not None:
            raise ValueError("A line shows a unit or held text, not both")
        return self


class FigureNumber(ContractModel):
    unit: UnitRef
    ref: str = Field(pattern=FIGURE_REF_PATTERN)


class FigureHead(ContractModel):
    number: FigureNumber | None = None
    title: UnitRef
    title_id: DomId | None = None
    dek: UnitRef | None = None
    dek_id: DomId | None = None

    @property
    def labelled_by(self) -> list[str]:
        return [name for name in (self.title_id, self.dek_id) if name]


class Placed(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    left: CssLength | None = None
    width: CssLength | None = None
    top: CssLength | None = None
    hidden: bool = False
    text: HeldText | None = None


class ToggleOption(ContractModel):
    value: str = Field(min_length=1)
    label: str = Field(min_length=1)
    pressed: bool


class ToggleGroup(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    label: str = Field(min_length=1)
    marker: Literal["layers", "zooms"]
    option_key: Literal["layer", "z"]
    options: list[ToggleOption] = Field(min_length=2)

    @model_validator(mode="after")
    def _one_option_pressed(self) -> Self:
        if sum(option.pressed for option in self.options) != 1:
            raise ValueError("A toggle group has exactly one option pressed")
        return self
