from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, HttpsUrl
from .component_specs_data_parts import ComponentLabel, FigureNumber, TextLine
from .component_specs_plates_parts import ClassName, DomId, HeldText, UnitRef

__all__ = [
    "SOURCE_LIST_SETTINGS",
    "CitationToolSpec",
    "ConceptAtlasSpec",
    "RelatedCraftsSpec",
    "SourceDisagreementsSpec",
    "SourceListSpec",
]

SOURCE_LIST_SETTINGS = ("status", "listing")
GRADES = ("A", "B", "C", "D")


class ConceptRow(ContractModel):
    name: str = Field(min_length=1)
    place: str = Field(min_length=1)
    family: str = Field(min_length=1)
    sentences: int = Field(ge=1)
    sentence: TextLine


class ConceptGroup(ContractModel):
    id: DomId
    title: UnitRef
    text: UnitRef
    together: UnitRef
    first: list[ConceptRow] = Field(min_length=1)
    more: list[ConceptRow] = Field(default_factory=list)


class ConceptAtlasSpec(ContractModel):
    title: UnitRef
    description: UnitRef
    groups: list[ConceptGroup] = Field(min_length=1)


class RelatedCraft(ContractModel):
    tile: int = Field(ge=1)
    swatch: HeldText
    top: str = Field(min_length=1)
    name: str = Field(min_length=1)
    place: str = Field(min_length=1)
    sources: int = Field(ge=1)
    monograph: bool
    gi: bool
    shares: HeldText
    sentence: UnitRef


class RelatedCraftsSpec(ContractModel):
    title: UnitRef
    kicker: str = Field(min_length=1)
    description: UnitRef
    weave: DomId
    crafts: list[RelatedCraft] = Field(min_length=1)


class ListedSource(ContractModel):
    key: str = Field(pattern=r"^g\d+$")
    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    meta: str = Field(min_length=1)
    grade: Literal[*GRADES]
    grade_label: str = Field(min_length=1)
    sentences: int = Field(ge=1)
    margin: str | None = None
    url: HttpsUrl
    link_label: str = Field(min_length=1)


class SourceListing(ContractModel):
    id: DomId
    title: UnitRef
    description: UnitRef
    open_label: str = Field(min_length=1)
    close_label: str = Field(min_length=1)
    sources: list[ListedSource] = Field(min_length=1)


class SourceListSpec(ContractModel):
    setting: Literal[*SOURCE_LIST_SETTINGS]
    status_id: DomId | None = None
    listing: SourceListing | None = None

    @model_validator(mode="after")
    def _the_part_of_its_setting(self) -> Self:
        if (self.status_id is not None) != (self.setting == "status"):
            raise ValueError("A status source list names its live region and nothing else")
        if (self.listing is not None) != (self.setting == "listing"):
            raise ValueError("A source listing has its listing part and no other")
        return self


class Reading(ContractModel):
    who: str = Field(min_length=1)
    unit: UnitRef


class RangeFigure(ContractModel):
    number: FigureNumber
    title: UnitRef
    dek: UnitRef
    chart: ComponentLabel
    source: UnitRef


class Disagreement(ContractModel):
    summary: HeldText
    readings: list[Reading] = Field(min_length=2)
    figure: RangeFigure | None = None


class SourceDisagreementsSpec(ContractModel):
    id: DomId
    title_id: DomId
    title: str = Field(min_length=1)
    intro: UnitRef
    items: list[Disagreement] = Field(min_length=1)


class CiteStyle(ContractModel):
    value: str = Field(pattern=r"^[a-z]+$")
    label: str = Field(min_length=1)
    text: str = Field(min_length=1)


class CitePanel(ContractModel):
    key: str = Field(pattern=r"^[a-z]+$")
    tab_id: DomId
    panel_id: DomId
    label: str = Field(min_length=1)
    box: list[ClassName] = Field(min_length=1)
    aid: str = Field(pattern=r"^[a-z]+$")
    cites: list[ClassName] = Field(min_length=1)
    box_id: DomId | None = None
    style_key: Literal["style", "cite-style"]
    styles: list[CiteStyle] = Field(min_length=1)
    text_id: DomId
    text: UnitRef
    link: UnitRef
    copy_label: str = Field(min_length=1)


class CitationToolSpec(ContractModel):
    title: UnitRef
    title_id: DomId
    tabs_label: str = Field(min_length=1)
    panels: list[CitePanel] = Field(min_length=1)

    @model_validator(mode="after")
    def _each_tab_names_its_own_panel(self) -> Self:
        ids = [panel.tab_id for panel in self.panels] + [panel.panel_id for panel in self.panels]
        if len(set(ids)) != len(ids):
            raise ValueError("Each citation tab and panel has its own id")
        return self
