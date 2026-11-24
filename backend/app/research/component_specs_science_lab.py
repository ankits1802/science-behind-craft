from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .component_specs_kit_scene import StillDrawing
from .component_specs_science_parts import (
    ComponentSlot,
    Differs,
    DomId,
    FigureKey,
    Label,
    Rich,
    SpecModel,
    TextBlock,
    UnitRef,
)

__all__ = [
    "ChoiceOption",
    "ChoiceToggleSpec",
    "ExperimentChoice",
    "ExperimentLabSpec",
    "FormulaChip",
]

KEY_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
Key = Annotated[str, Field(pattern=KEY_PATTERN)]
Cid = Annotated[int, Field(ge=1)]


class ResultText(SpecModel):
    part: Literal["text"]
    unit: UnitRef


class ResultDiffers(SpecModel):
    part: Literal["differs"]
    differs: Differs


ResultPart = Annotated[ResultText | ResultDiffers, Field(discriminator="part")]


class ChoiceOption(SpecModel):
    value: Key
    label: Label
    heading: UnitRef
    parts: list[ResultPart] = Field(min_length=1)


class FormulaChip(SpecModel):
    formula: Rich
    name: Label
    cid: Cid | None = None
    source: Label | None = None

    @model_validator(mode="after")
    def _a_record_or_its_source(self) -> Self:
        if (self.cid is None) == (self.source is None):
            raise ValueError(
                f"formula {self.name!r} links its PubChem record or names its source, one of them"
            )
        return self


class FormulaSet(SpecModel):
    part: Literal["formulas"]
    option: Key | None = None
    chips: list[FormulaChip] = Field(min_length=1)


class SameNote(SpecModel):
    part: Literal["same"]
    label: UnitRef
    paragraphs: list[UnitRef] = Field(min_length=1)


class PanelText(SpecModel):
    part: Literal["text"]
    text: TextBlock


class DaysChart(SpecModel):
    part: Literal["chart"]
    title: UnitRef
    chart: ComponentSlot
    source: UnitRef


class StageBox(SpecModel):
    part: Literal["stage"]
    drawing: StillDrawing
    note: UnitRef | None = None
    note_hook: Key | None = None


class Stepper(SpecModel):
    part: Literal["stepper"]
    hook: Key
    action: Rich
    status_hook: Key
    status: Label


class Switch(SpecModel):
    part: Literal["switch"]
    hook: Key
    label: Rich
    description: Label


PanelLeaf = Annotated[
    PanelText | FormulaSet | SameNote | DaysChart | StageBox | Stepper | Switch, Field(discriminator="part")
]


class MoreBox(SpecModel):
    part: Literal["more"]
    parts: list[PanelLeaf] = Field(min_length=1)


PanelPart = Annotated[
    PanelText | FormulaSet | SameNote | DaysChart | StageBox | Stepper | Switch | MoreBox,
    Field(discriminator="part"),
]


class ChoiceToggleSpec(SpecModel):
    experiment: Key
    question_id: DomId
    question: UnitRef
    options: list[ChoiceOption] = Field(min_length=2)
    text_parts: list[PanelPart] = Field(default_factory=list)
    visual_parts: list[PanelPart] = Field(default_factory=list)

    @model_validator(mode="after")
    def _options_named_once(self) -> Self:
        values = [option.value for option in self.options]
        if len(set(values)) != len(values):
            raise ValueError(f"toggle {self.experiment} names each option once")
        return self


class ExperimentChoice(SpecModel):
    key: Key
    label: Label
    toggle: ComponentSlot


class ExperimentLabSpec(SpecModel):
    id: DomId
    figure: FigureKey
    number: UnitRef
    picker_label: Label
    experiments: list[ExperimentChoice] = Field(min_length=2)
