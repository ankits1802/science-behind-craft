from __future__ import annotations

import re
import uuid
from collections.abc import Iterator, Mapping, Sequence
from itertools import pairwise
from types import MappingProxyType
from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .blocks import SENTENCE, BlockBase, ExplainerSentence, SentenceSpec, named_in, require_facts

__all__ = [
    "DIPS_MAX",
    "FIRING_ATMOSPHERES",
    "INDIGO_FORMS",
    "LOST_WAX_STEPS",
    "SIGNATURE_KINDS",
    "SIGNATURE_TERMS",
    "SWATCHES_MAX",
    "VAT_KINDS",
    "CompoundRef",
    "FiringAtmosphere",
    "FiringBlock",
    "FiringTemperature",
    "IndigoForm",
    "IndigoVatBlock",
    "LostWaxBlock",
    "LostWaxStep",
    "MordantBathBlock",
    "MordantSwatch",
    "SignatureBlock",
    "VatContent",
    "VatDip",
    "chosen_signature",
]

SIGNATURE_KINDS = ("indigo_vat", "mordant_bath", "lost_wax", "firing")
VAT_KINDS = ("FERMENTED", "CHEMICAL")
INDIGO_FORMS = ("KETO", "LEUCO")
LOST_WAX_STEPS = ("MODEL", "JACKET", "BURNOUT", "POUR", "BREAK_OUT")
FIRING_ATMOSPHERES = ("OXIDISING", "REDUCING")
DIPS_MAX = 8
SWATCHES_MAX = 4
VAT_CONTENTS_MAX = 8
STATED_MAX_CHARS = 120
NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight")
ORDINAL_WORDS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth")
SIGNATURE_TERMS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "indigo_vat": frozenset({"indigo", "leucoindigo", "indigo-vat", "naand", "indigofera", "neel"}),
        "mordant_bath": frozenset(
            {"mordant", "alum", "iron-acetate", "kut", "harde", "myrobalan", "tannin", "madder", "alizarin"}
        ),
        "lost_wax": frozenset({"lost-wax", "lost-wax-casting", "cire-perdue", "dhokra", "wax-model"}),
        "firing": frozenset(
            {"firing", "kiln", "terracotta", "glaze", "reduction-firing", "oxidising-firing"}
        ),
    }
)

Stated = Annotated[str, Field(min_length=1, max_length=STATED_MAX_CHARS)]


class CompoundRef(ContractModel):
    compound_id: uuid.UUID
    pubchem_cid: int = Field(ge=1)
    formula: str | None = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1)


class IndigoForm(ContractModel):
    form: Literal[*INDIGO_FORMS]
    name: Stated
    colour: Stated
    soluble: bool
    compound: CompoundRef | None
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _named_by_its_sentence(self) -> Self:
        _require_named(f"the {self.form.lower()} form", [self.name, self.colour], self.sentence)
        return self


class VatDip(ContractModel):
    dips: int = Field(ge=1, le=DIPS_MAX)
    stated: Stated
    shade: Stated | None
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _a_count_its_source_states(self) -> Self:
        _require_named(
            f"{self.dips} dips", [self.stated, *([self.shade] if self.shade else [])], self.sentence
        )
        if not _states_count(self.stated, self.dips):
            raise ValueError(f"{self.stated!r} does not state {self.dips} dips")
        return self


class VatContent(ContractModel):
    name: Stated
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _named_by_its_sentence(self) -> Self:
        _require_named("a vat content", [self.name], self.sentence)
        return self


class IndigoVatBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (
        ("lift", SENTENCE),
        ("forms", [(("sentence", SENTENCE),)]),
        ("dips", [(("sentence", SENTENCE),)]),
        ("contents", [(("sentence", SENTENCE),)]),
    )

    kind: Literal["indigo_vat"]
    version: Literal[1]
    vat: Literal[*VAT_KINDS]
    lift: ExplainerSentence
    forms: list[IndigoForm] = Field(max_length=len(INDIGO_FORMS))
    dips: list[VatDip] = Field(max_length=DIPS_MAX)
    contents: list[VatContent] = Field(max_length=VAT_CONTENTS_MAX)

    @model_validator(mode="after")
    def _one_vat_told_by_its_sources(self) -> Self:
        require_facts(f"indigo vat {self.id}", list(self.cited_sentences()))
        _require_once(f"indigo vat {self.id}", [form.form for form in self.forms], "form")
        if any(a.dips >= b.dips for a, b in pairwise(self.dips)):
            raise ValueError(f"indigo vat {self.id} lists dips by rising count, each once")
        _require_once(f"indigo vat {self.id}", [c.name.casefold() for c in self.contents], "content")
        return self

    def direct_source_ids(self) -> Iterator[str]:
        yield from (form.compound.source_id for form in self.forms if form.compound is not None)

    def shown_labels(self) -> list[str]:
        return [*(form.name for form in self.forms), *(content.name for content in self.contents)]


class MordantSwatch(ContractModel):
    mordant: Stated | None
    colour: Stated
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _named_by_its_sentence(self) -> Self:
        _require_named("a swatch", [self.colour, *([self.mordant] if self.mordant else [])], self.sentence)
        return self


class MordantBathBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("swatches", [(("sentence", SENTENCE),)]),)

    kind: Literal["mordant_bath"]
    version: Literal[1]
    dye: Stated
    fibre: Stated
    swatches: list[MordantSwatch] = Field(min_length=1, max_length=SWATCHES_MAX)

    @model_validator(mode="after")
    def _swatches_its_sources_describe(self) -> Self:
        require_facts(f"mordant bath {self.id}", list(self.cited_sentences()))
        mordants = [(swatch.mordant or "").casefold() for swatch in self.swatches]
        _require_once(f"mordant bath {self.id}", mordants, "mordant, or no mordant,")
        sentences = [swatch.sentence for swatch in self.swatches]
        for name in (self.dye, self.fibre):
            if not any(named_in(name, sentence) for sentence in sentences):
                raise ValueError(f"mordant bath {self.id} names {name!r}, which no swatch sentence states")
        return self

    def shown_labels(self) -> list[str]:
        return [self.dye, self.fibre, *(swatch.mordant for swatch in self.swatches if swatch.mordant)]


class LostWaxStep(ContractModel):
    step: Literal[*LOST_WAX_STEPS]
    sentence: ExplainerSentence


class LostWaxBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("steps", [(("sentence", SENTENCE),)]),)

    kind: Literal["lost_wax"]
    version: Literal[1]
    metal: Stated
    steps: list[LostWaxStep] = Field(min_length=1, max_length=len(LOST_WAX_STEPS))

    @model_validator(mode="after")
    def _steps_in_casting_order(self) -> Self:
        require_facts(f"lost wax {self.id}", list(self.cited_sentences()))
        places = [LOST_WAX_STEPS.index(step.step) for step in self.steps]
        if any(a >= b for a, b in pairwise(places)):
            raise ValueError(f"lost wax {self.id} shows each step once, in casting order")
        if not any(named_in(self.metal, step.sentence) for step in self.steps):
            raise ValueError(f"lost wax {self.id} names {self.metal!r}, which no step sentence states")
        return self

    def shown_labels(self) -> list[str]:
        return [self.metal]


class FiringAtmosphere(ContractModel):
    atmosphere: Literal[*FIRING_ATMOSPHERES]
    colour: Stated
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _named_by_its_sentence(self) -> Self:
        _require_named(f"the {self.atmosphere.lower()} firing", [self.colour], self.sentence)
        return self


class FiringTemperature(ContractModel):
    stated: Stated
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _a_temperature_its_source_states(self) -> Self:
        _require_named("a firing temperature", [self.stated], self.sentence)
        return self


class FiringBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (
        ("atmospheres", [(("sentence", SENTENCE),)]),
        ("temperature", (("sentence", SENTENCE),)),
    )

    kind: Literal["firing"]
    version: Literal[1]
    body: Stated
    atmospheres: list[FiringAtmosphere] = Field(min_length=1, max_length=len(FIRING_ATMOSPHERES))
    temperature: FiringTemperature | None

    @model_validator(mode="after")
    def _atmospheres_its_sources_describe(self) -> Self:
        sentences = list(self.cited_sentences())
        require_facts(f"firing {self.id}", sentences)
        _require_once(f"firing {self.id}", [a.atmosphere for a in self.atmospheres], "atmosphere")
        if not any(named_in(self.body, sentence) for sentence in sentences):
            raise ValueError(f"firing {self.id} names {self.body!r}, which no sentence states")
        return self

    def shown_labels(self) -> list[str]:
        return [self.body]


SignatureBlock = Annotated[
    IndigoVatBlock | MordantBathBlock | LostWaxBlock | FiringBlock, Field(discriminator="kind")
]


def chosen_signature(term_keys: Sequence[str]) -> str | None:
    for key in term_keys:
        for kind in SIGNATURE_KINDS:
            if key in SIGNATURE_TERMS[kind]:
                return kind
    return None


def _require_named(owner: str, names: Sequence[str], sentence: ExplainerSentence) -> None:
    unstated = [name for name in names if not named_in(name, sentence)]
    if unstated:
        raise ValueError(f"{owner} shows {', '.join(map(repr, unstated))}, which its sentence does not state")


def _require_once(owner: str, values: Sequence[str], noun: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{owner} shows each {noun} once")


def _states_count(stated: str, count: int) -> bool:
    words = set(re.findall(r"[^\W_]+", stated.casefold()))
    return bool(words & {str(count), NUMBER_WORDS[count - 1], ORDINAL_WORDS[count - 1]})
