from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from app.models.enums import ENVIRONMENT_FACTORS, PLACE_ROLES

from .base import ContractModel
from .blocks import DifferReading, ExplainerSentence, require_facts, require_findings
from .citations import Citation
from .craft_contributed import CONTRIBUTED_PER_CHAPTER_MAX, ContributedPlate
from .craft_origins import PageAiMedia
from .craft_page_context import SAME_FAMILY_MAX, PageRelative
from .datasets import DatasetRef
from .field_voices import FIELD_PHOTOS_SHOWN, PageFieldPhoto
from .media_refs import MediaRef

__all__ = [
    "RESEARCH_QUESTIONS",
    "SOURCE_GROUPS",
    "AiMediaPart",
    "AreaName",
    "ChapterCommunity",
    "ChapterPlace",
    "CommunitiesPart",
    "ContributedPart",
    "EntryPlace",
    "FamilyLink",
    "FieldPhotosPart",
    "Focal",
    "KeyFactsPart",
    "LabelledFact",
    "OpenQuestion",
    "OpenQuestionsPart",
    "PagePart",
    "PagePlate",
    "PictureCredit",
    "PlacesPart",
    "PlatePart",
    "RecordEntry",
    "RecordPart",
    "RegisterFact",
    "RegisterFactsPart",
    "RelativesPart",
    "Searched",
    "SearchedPart",
    "SourceGroupList",
    "SourceListPart",
    "SourcesDifferPart",
    "StartResearchPart",
]

SOURCE_GROUPS = (
    "GOVERNMENT",
    "SCHOLARSHIP",
    "MUSEUM",
    "WEB_AND_PRESS",
    "FIELD",
    "FAMILY",
    "KIN",
    "LIBRARY",
    "COMPOUND_RECORDS",
)
RESEARCH_QUESTIONS = 3
FOCAL_EDGE = 1.0

Sentences = list[ExplainerSentence]


class Focal(ContractModel):
    x: float = Field(ge=0, le=FOCAL_EDGE)
    y: float = Field(ge=0, le=FOCAL_EDGE)
    width: float = Field(gt=0, le=FOCAL_EDGE)
    height: float = Field(gt=0, le=FOCAL_EDGE)

    @model_validator(mode="after")
    def _inside_the_picture(self) -> Self:
        if self.x + self.width > FOCAL_EDGE or self.y + self.height > FOCAL_EDGE:
            raise ValueError("a focal box lies inside its picture")
        return self


class PagePlate(ContractModel):
    media: MediaRef
    caption: str = Field(min_length=1, max_length=300)
    stand_in: str | None = Field(min_length=1, max_length=200)
    focal: Focal | None
    sentences: Sentences

    @model_validator(mode="after")
    def _a_licensed_picture_with_facts(self) -> Self:
        if self.media.display != "INLINE":
            raise ValueError(f"plate {self.media.id} shows only a picture drawn inline")
        require_facts(f"plate {self.media.id}", self.sentences)
        return self


class _Part(ContractModel):
    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        yield from ()

    def plates(self) -> Iterator[PagePlate]:
        yield from ()

    def shown_media(self) -> Iterator[MediaRef]:
        for plate in self.plates():
            yield plate.media

    def citations(self) -> Iterator[Citation]:
        for sentence in self.cited_sentences():
            yield from sentence.citations
        for plate in self.plates():
            for sentence in plate.sentences:
                yield from sentence.citations

    def cited_source_ids(self) -> list[str]:
        return list(dict.fromkeys(citation.source_id for citation in self.citations()))


class LabelledFact(ContractModel):
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=300)
    citations: list[Citation] = Field(min_length=1)


class KeyFactsPart(_Part):
    kind: Literal["key_facts"]
    facts: list[LabelledFact] = Field(min_length=1)

    def citations(self) -> Iterator[Citation]:
        for fact in self.facts:
            yield from fact.citations


class RegisterFact(ContractModel):
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=300)


class RegisterFactsPart(_Part):
    kind: Literal["register_facts"]
    facts: list[RegisterFact] = Field(min_length=1)


class PlatePart(_Part):
    kind: Literal["plate"]
    plate: PagePlate

    def plates(self) -> Iterator[PagePlate]:
        yield self.plate


class EntryPlace(ContractModel):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)


class RecordEntry(ContractModel):
    label: str = Field(min_length=1, max_length=120)
    start: int | None
    end: int | None
    factor: Literal[*ENVIRONMENT_FACTORS] | None
    place: EntryPlace | None
    sentences: Sentences = Field(min_length=1)
    plate: PagePlate | None

    @model_validator(mode="after")
    def _a_span_or_a_factor(self) -> Self:
        require_facts(f"record entry {self.label!r}", self.sentences)
        if (self.start is None) != (self.end is None):
            raise ValueError(f"record entry {self.label!r} gives its span's start and end together")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError(f"record entry {self.label!r} starts before it ends")
        return self


class RecordPart(_Part):
    kind: Literal["record"]
    entries: list[RecordEntry] = Field(min_length=1)

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for entry in self.entries:
            yield from entry.sentences

    def plates(self) -> Iterator[PagePlate]:
        yield from (entry.plate for entry in self.entries if entry.plate is not None)


class SourcesDifferPart(_Part):
    kind: Literal["sources_differ"]
    reading: DifferReading

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        yield from self.reading.sentences()


class AreaName(ContractModel):
    lgd: int | None
    name: str = Field(min_length=1)


class ChapterPlace(ContractModel):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    roles: list[Literal[*PLACE_ROLES]] = Field(min_length=1)
    district: AreaName | None
    state: AreaName | None
    country: str = Field(min_length=1)
    wikidata_id: str | None
    sentences: Sentences = Field(min_length=1)


class PlacesPart(_Part):
    kind: Literal["places"]
    places: list[ChapterPlace] = Field(min_length=1)

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for place in self.places:
            yield from place.sentences


class ChapterCommunity(ContractModel):
    key: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    local_names: list[str]
    honours: list[str]
    place: str | None
    place_key: str | None
    sentences: Sentences = Field(min_length=1)


class CommunitiesPart(_Part):
    kind: Literal["communities"]
    communities: list[ChapterCommunity] = Field(min_length=1)

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for community in self.communities:
            yield from community.sentences


class FieldPhotosPart(_Part):
    kind: Literal["field_photos"]
    photos: list[PageFieldPhoto] = Field(min_length=1, max_length=FIELD_PHOTOS_SHOWN)
    total: int = Field(ge=1)

    @model_validator(mode="after")
    def _no_more_than_counted(self) -> Self:
        if len(self.photos) > self.total:
            raise ValueError("field photographs show no more than they count")
        return self


class FamilyLink(ContractModel):
    label: str = Field(min_length=1)
    path: str = Field(pattern=r"^/categories/[A-Za-z0-9-]+$")


class RelativesPart(_Part):
    kind: Literal["relatives"]
    crafts: list[PageRelative] = Field(max_length=SAME_FAMILY_MAX)
    family: FamilyLink | None

    @model_validator(mode="after")
    def _kin_or_a_family(self) -> Self:
        if not self.crafts and self.family is None:
            raise ValueError("relatives show a craft or the family page")
        return self

    def citations(self) -> Iterator[Citation]:
        for relative in self.crafts:
            if relative.lede is not None:
                yield from relative.lede.citations

    def shown_media(self) -> Iterator[MediaRef]:
        yield from (relative.hero.media for relative in self.crafts if relative.hero is not None)


class SourceGroupList(ContractModel):
    group: Literal[*SOURCE_GROUPS]
    title: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class PictureCredit(ContractModel):
    media_id: uuid.UUID
    credit: str = Field(min_length=1, max_length=600)


class SourceListPart(_Part):
    kind: Literal["source_list"]
    groups: list[SourceGroupList] = Field(min_length=1)
    datasets: list[DatasetRef]
    pictures: list[PictureCredit]

    @model_validator(mode="after")
    def _each_source_once(self) -> Self:
        ids = [source_id for group in self.groups for source_id in group.source_ids]
        if len(set(ids)) != len(ids) or len({group.group for group in self.groups}) != len(self.groups):
            raise ValueError("the source list files each source once, in one group each")
        return self


class OpenQuestion(ContractModel):
    key: str | None
    question: str = Field(min_length=1)
    settled_by: str | None
    sentences: Sentences = Field(min_length=1)


class OpenQuestionsPart(_Part):
    kind: Literal["open_questions"]
    questions: list[OpenQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def _stored_findings(self) -> Self:
        for question in self.questions:
            require_findings(f"open question {question.question!r}", question.sentences)
        return self

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for question in self.questions:
            yield from question.sentences


class Searched(ContractModel):
    query: str = Field(min_length=1)
    site: str = Field(min_length=1)


class SearchedPart(_Part):
    kind: Literal["searched"]
    searched: list[Searched] = Field(min_length=1)


class StartResearchPart(_Part):
    kind: Literal["start_research"]
    questions: list[str] = Field(min_length=RESEARCH_QUESTIONS, max_length=RESEARCH_QUESTIONS)


class AiMediaPart(_Part):
    kind: Literal["ai_media"]
    media: list[PageAiMedia] = Field(min_length=1)

    @model_validator(mode="after")
    def _each_asset_once(self) -> Self:
        ids = [item.asset_id for item in self.media]
        if len(set(ids)) != len(ids):
            raise ValueError("an AI asset is drawn once")
        return self

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for item in self.media:
            yield from item.sentences


class ContributedPart(_Part):
    kind: Literal["contributed"]
    pictures: list[ContributedPlate] = Field(min_length=1, max_length=CONTRIBUTED_PER_CHAPTER_MAX)

    @model_validator(mode="after")
    def _each_picture_once(self) -> Self:
        ids = [plate.contribution_id for plate in self.pictures]
        if len(set(ids)) != len(ids):
            raise ValueError("a contributed picture is drawn once")
        return self

    def cited_sentences(self) -> Iterator[ExplainerSentence]:
        for plate in self.pictures:
            yield from plate.sentences


PagePart = Annotated[
    KeyFactsPart
    | RegisterFactsPart
    | PlatePart
    | RecordPart
    | SourcesDifferPart
    | PlacesPart
    | CommunitiesPart
    | FieldPhotosPart
    | RelativesPart
    | SourceListPart
    | OpenQuestionsPart
    | SearchedPart
    | StartResearchPart
    | AiMediaPart
    | ContributedPart,
    Field(discriminator="kind"),
]
