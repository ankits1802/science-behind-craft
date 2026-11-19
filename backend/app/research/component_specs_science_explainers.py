from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from .component_specs_science_parts import (
    ColourToken,
    ComponentSlot,
    DomId,
    FigureHead,
    Label,
    Rich,
    SpecModel,
    StyleName,
    SvgNode,
    UnitRef,
)

__all__ = [
    "ExplainerControls",
    "ExplainerKeyItem",
    "ExplainerStill",
    "MaterialCard",
    "MaterialCardsSpec",
    "ModelDocument",
    "ModelExplainerSpec",
    "ProcessReplaySpec",
    "ReplaySection",
    "ReplaySource",
    "ReplayStage",
]

FRAME_SANDBOX = "allow-scripts"
DOCUMENT_MAX_CHARS = 400_000
GRADES = ("A", "B", "C", "D")


class MaterialCard(SpecModel):
    swatch: ColourToken | Literal["crystal"]
    role: UnitRef
    name: UnitRef
    local: UnitRef
    botanical: UnitRef | None = None
    chemistry: UnitRef
    facts: list[UnitRef] = Field(min_length=1)


class MaterialCardsSpec(SpecModel):
    id: DomId
    heading_id: DomId
    heading: Label
    intro: UnitRef
    cards: list[MaterialCard] = Field(min_length=1)
    after: list[ComponentSlot] = Field(default_factory=list)


class ExplainerStill(SpecModel):
    width: Literal["wide", "narrow"]
    heading: UnitRef
    lede: UnitRef
    drawing: SvgNode
    phase: UnitRef
    numbers: UnitRef


class ExplainerControls(SpecModel):
    play: Label
    play_icon: SvgNode
    slider_label: Label
    slider_max: int = Field(ge=1)
    slider_at: int = Field(ge=0)
    ticks: list[Label] = Field(min_length=2)

    @model_validator(mode="after")
    def _at_rest_on_the_slider(self) -> Self:
        if self.slider_at > self.slider_max:
            raise ValueError("the slider rests within its range")
        return self


class ExplainerKeyItem(SpecModel):
    style: StyleName | None = None
    icon: SvgNode
    label: Label


class ModelDocument(SpecModel):
    title: Label
    height: int = Field(ge=1)
    stylesheet: str = Field(min_length=1, pattern=r"^[^<]*$")
    document: str = Field(min_length=1, max_length=DOCUMENT_MAX_CHARS)
    sandbox: Literal["allow-scripts"] = FRAME_SANDBOX


class ModelExplainerSpec(SpecModel):
    head: FigureHead
    badge: Label
    badge_note: Label
    stills: list[ExplainerStill] = Field(min_length=1)
    controls: ExplainerControls
    key: list[ExplainerKeyItem] = Field(min_length=1)
    model: ModelDocument


class ReplayStage(SpecModel):
    label: Label
    detail: Label
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=1)

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> Self:
        if self.end_ms <= self.start_ms:
            raise ValueError(f"replay stage {self.label!r} ends after it starts")
        return self


class ReplaySource(SpecModel):
    title: Label
    grade: Literal[*GRADES]


class ReplaySection(SpecModel):
    title: Label
    made: Rich


class ProcessReplaySpec(SpecModel):
    play: Label
    understood: UnitRef
    angles: UnitRef
    stages: list[ReplayStage] = Field(min_length=1)
    sources_kicker: UnitRef
    sources: list[ReplaySource] = Field(min_length=1)
    sections_kicker: UnitRef
    sections: list[ReplaySection] = Field(min_length=1)
    ready: UnitRef
