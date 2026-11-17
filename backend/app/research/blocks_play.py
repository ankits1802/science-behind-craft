from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator, Sequence
from typing import ClassVar, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.core.errors import InvalidInput

from .base import ContractModel
from .blocks import (
    SENTENCE,
    BlockBase,
    ExplainerSentence,
    SentenceSpec,
    named_in,
    require_findings,
    stated_texts,
)
from .citations import Citation
from .datasets import DATASET_CODE_PATTERN, DatasetRef, dataset_codes_problems
from .quotes import figures_in, quote_occurs, unsupported_figures
from .sandbox import SANDBOX_MAX_BYTES, sandbox_problems
from .subject_keys import TermKey, term_key

__all__ = [
    "SIMULATION_MAX_BYTES",
    "SIMULATION_VALUES_MAX",
    "SIMULATION_VALUE_KEY_PATTERN",
    "WHAT_IF_OPTIONS_MAX",
    "WHAT_IF_OUTCOMES_MAX",
    "SimulationBlock",
    "SimulationValue",
    "WhatIfBlock",
    "WhatIfOption",
    "WhatIfOutcome",
    "hidden_block",
    "simulation_concept_key",
]

SIMULATION_MAX_BYTES = SANDBOX_MAX_BYTES
SIMULATION_VALUES_MAX = 40
SIMULATION_VALUE_KEY_PATTERN = r"^[a-z][a-zA-Z0-9]{0,39}$"
WHAT_IF_OPTIONS_MAX = 6
WHAT_IF_OUTCOMES_MAX = 3


class SimulationValue(ContractModel):
    key: str = Field(pattern=SIMULATION_VALUE_KEY_PATTERN)
    label: str = Field(min_length=1, max_length=120)
    value: float
    unit: str | None = Field(min_length=1, max_length=40)
    stated: str | None = Field(min_length=1, max_length=200)
    citations: list[Citation]
    dataset_code: str | None = Field(pattern=DATASET_CODE_PATTERN, max_length=80)

    @model_validator(mode="after")
    def _a_figure_its_source_states(self) -> Self:
        if self.dataset_code is not None:
            if self.citations or self.stated is not None:
                raise ValueError(f"value {self.key} rests on its dataset row or on cited quotes, not both")
            return self
        if not self.citations or self.stated is None:
            raise ValueError(f"value {self.key} is a figure a cited quote states, or a dataset row value")
        if not any(c.quote and quote_occurs(self.stated, c.quote) for c in self.citations):
            raise ValueError(f"value {self.key} states {self.stated!r}, which no cited quote says")
        if not _figure_of(self.value, [self.stated]):
            raise ValueError(f"value {self.key} is {self.value}, a figure {self.stated!r} does not state")
        if unsupported_figures(self.label, [self.stated]):
            raise ValueError(f"value {self.key} is labelled with a figure its quote does not state")
        return self


class SimulationBlock(BlockBase):
    kind: Literal["simulation"]
    version: Literal[1]
    concept: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=120)
    created_at: AwareDatetime
    html: str = Field(min_length=1)
    html_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    values: list[SimulationValue] = Field(min_length=1, max_length=SIMULATION_VALUES_MAX)
    datasets: list[DatasetRef]
    hidden: bool

    @model_validator(mode="after")
    def _fed_only_cited_values_and_sandboxed(self) -> Self:
        keys = [value.key for value in self.values]
        if len(set(keys)) != len(keys):
            raise ValueError(f"simulation {self.id} passes each value once")
        if hashlib.sha256(self.html.encode("utf-8")).hexdigest() != self.html_sha256:
            raise ValueError(f"simulation {self.id} names the SHA-256 of its own HTML")
        simulation_concept_key(self.concept)
        stated = [value.stated for value in self.values if value.stated]
        if unsupported_figures(self.title, stated) or unsupported_figures(self.concept, stated):
            raise ValueError(f"simulation {self.id} titles itself with a figure no value states")
        used = [value.dataset_code for value in self.values if value.dataset_code]
        problems = dataset_codes_problems(f"simulation {self.id}", self.datasets, used)
        if {dataset.code for dataset in self.datasets} - set(used):
            problems.append(f"simulation {self.id} cites only the dataset rows its values use")
        sandboxed = sandbox_problems(self.html, {value.key: value.value for value in self.values})
        problems += [f"simulation {self.id} fails the sandbox check: {p.rule} {p.detail}" for p in sandboxed]
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def citations(self) -> Iterator[Citation]:
        for value in self.values:
            yield from value.citations

    def cites_datasets(self) -> bool:
        return bool(self.datasets)

    def shown_labels(self) -> list[str]:
        return [self.title, self.concept, *(value.label for value in self.values)]


def hidden_block(block: BlockBase) -> bool:
    return isinstance(block, SimulationBlock) and block.hidden


def simulation_concept_key(concept: str) -> str:
    try:
        return term_key(concept)
    except InvalidInput as error:
        raise ValueError(f"concept {concept!r} has no Latin letter or digit to key it by") from error


class WhatIfOutcome(ContractModel):
    sentence: ExplainerSentence
    reaction_id: uuid.UUID | None


class WhatIfOption(ContractModel):
    label: str = Field(min_length=1, max_length=200)
    material_id: uuid.UUID | None
    term_key: TermKey | None
    outcomes: list[WhatIfOutcome] = Field(max_length=WHAT_IF_OUTCOMES_MAX)

    @model_validator(mode="after")
    def _outcomes_only_from_its_evidence(self) -> Self:
        texts = [text for outcome in self.outcomes for text in stated_texts(outcome.sentence)]
        if unsupported_figures(self.label, texts):
            raise ValueError(f"option {self.label!r} carries a figure its outcomes do not state")
        stored = self.material_id is not None or self.term_key is not None
        if not stored and not all(named_in(self.label, outcome.sentence) for outcome in self.outcomes):
            raise ValueError(f"option {self.label!r} is neither stored nor named by each of its outcomes")
        claims = [frozenset(c.claim_id for c in outcome.sentence.citations) for outcome in self.outcomes]
        if len(set(claims)) != len(claims):
            raise ValueError(f"option {self.label!r} states each outcome once")
        return self


class WhatIfBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("options", [(("outcomes", [(("sentence", SENTENCE),)]),)]),)

    kind: Literal["what_if"]
    version: Literal[1]
    changed: str = Field(min_length=1, max_length=200)
    stage_id: uuid.UUID | None
    options: list[WhatIfOption] = Field(min_length=2, max_length=WHAT_IF_OPTIONS_MAX)

    @model_validator(mode="after")
    def _one_input_its_options_once_each(self) -> Self:
        require_findings(f"what if {self.id}", list(self.cited_sentences()))
        labels = [option.label.casefold() for option in self.options]
        if len(set(labels)) != len(labels):
            raise ValueError(f"what if {self.id} offers each option once")
        texts = [text for sentence in self.cited_sentences() for text in stated_texts(sentence)]
        if unsupported_figures(self.changed, texts):
            raise ValueError(f"what if {self.id} changes an input named with a figure no outcome states")
        return self

    def shown_labels(self) -> list[str]:
        return [self.changed, *(option.label for option in self.options)]


def _figure_of(value: float, texts: Sequence[str]) -> bool:
    return any(_as_number(figure) == value for text in texts for figure in figures_in(text))


def _as_number(figure: str) -> float | None:
    try:
        return float(figure)
    except ValueError:
        return None
