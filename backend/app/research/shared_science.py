from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from pydantic import Field, ValidationError, model_validator

from .base import ContractModel
from .blocks_learning import (
    COMPARE_CRAFTS_MIN,
    CONCEPT_CRAFTS_MAX,
    CONCEPT_NODES_MAX,
    ConceptCraft,
    ConceptNode,
)
from .citations import SourceRef, cited_source_ids
from .crafts import CraftRef
from .offered_facts import OfferedFact, first_naming, shown_sentence, term_marker

__all__ = [
    "SHARED_SCIENCE_NODES_MAX",
    "SHARED_SCIENCE_SCHEMA_VERSION",
    "SharedConcept",
    "SharedScience",
    "TermCraftOffer",
    "TermOffer",
    "concept_node",
    "shared_concept",
    "shared_science",
]

logger = logging.getLogger(__name__)

SHARED_SCIENCE_SCHEMA_VERSION = 1
SHARED_SCIENCE_NODES_MAX = 3 * CONCEPT_NODES_MAX


class SharedScience(ContractModel):
    schema_version: Literal[1]
    craft: CraftRef
    nodes: list[ConceptNode] = Field(max_length=SHARED_SCIENCE_NODES_MAX)
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _the_craft_s_shared_concepts(self) -> Self:
        keys = [node.term_key for node in self.nodes]
        if len(set(keys)) != len(keys):
            raise ValueError(f"the shared science of {self.craft.slug} shows each concept once")
        if any(all(entry.craft.slug != self.craft.slug for entry in node.crafts) for node in self.nodes):
            raise ValueError(f"the shared science of {self.craft.slug} shows only concepts it shares")
        _require_sources(self.sources, self.nodes)
        return self


class SharedConcept(ContractModel):
    schema_version: Literal[1]
    node: ConceptNode
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _every_craft_cited(self) -> Self:
        _require_sources(self.sources, [self.node])
        return self


@dataclass(frozen=True)
class TermCraftOffer:
    craft: CraftRef
    concept_ids: tuple[uuid.UUID, ...]
    facts: tuple[OfferedFact, ...]


@dataclass(frozen=True)
class TermOffer:
    key: str
    label: str
    surfaces: tuple[str, ...]
    crafts: tuple[TermCraftOffer, ...]


def concept_node(offer: TermOffer, *, focus: str | None, id_prefix: str = "") -> ConceptNode | None:
    found: list[tuple[TermCraftOffer, OfferedFact]] = []
    for entry in offer.crafts:
        own = [fact for fact in entry.facts if fact.concept_id in entry.concept_ids]
        fact = first_naming(own, offer.label)
        if fact is not None:
            found.append((entry, fact))
    ordered = sorted(found, key=lambda pair: _craft_order(pair[0].craft, focus))[:CONCEPT_CRAFTS_MAX]
    if len(ordered) < COMPARE_CRAFTS_MIN:
        return None
    if focus is not None and ordered[0][0].craft.slug != focus:
        return None
    marker = term_marker(offer.key, offer.surfaces)
    try:
        return ConceptNode(
            term_key=offer.key,
            label=offer.label,
            crafts=[
                ConceptCraft(
                    craft=entry.craft,
                    concept_ids=list(entry.concept_ids),
                    sentence=shown_sentence(fact, f"{id_prefix}{offer.key}.{number}", marker),
                )
                for number, (entry, fact) in enumerate(ordered, start=1)
            ],
        )
    except ValidationError as refused:
        logger.warning("the shared concept %s is not shown: %s", offer.key, refused)
        return None


def shared_science(
    craft: CraftRef, offers: Sequence[TermOffer], sources: Mapping[str, SourceRef]
) -> SharedScience:
    nodes = [node for node in (concept_node(offer, focus=craft.slug) for offer in offers) if node is not None]
    nodes = sorted(nodes, key=lambda node: (node.label.casefold(), node.term_key))[:SHARED_SCIENCE_NODES_MAX]
    return SharedScience(
        schema_version=SHARED_SCIENCE_SCHEMA_VERSION,
        craft=craft,
        nodes=nodes,
        sources=_cited(nodes, sources),
    )


def shared_concept(
    offer: TermOffer, sources: Mapping[str, SourceRef], *, focus: str | None = None
) -> SharedConcept | None:
    node = concept_node(offer, focus=focus)
    if node is None:
        return None
    return SharedConcept(
        schema_version=SHARED_SCIENCE_SCHEMA_VERSION, node=node, sources=_cited([node], sources)
    )


def _craft_order(craft: CraftRef, focus: str | None) -> tuple[bool, str, str]:
    return craft.slug != focus, craft.name.casefold(), craft.slug


def _cited(nodes: Sequence[ConceptNode], sources: Mapping[str, SourceRef]) -> list[SourceRef]:
    sentences = [entry.sentence for node in nodes for entry in node.crafts]
    return [sources[source_id] for source_id in cited_source_ids(sentences)]


def _require_sources(sources: Sequence[SourceRef], nodes: Sequence[ConceptNode]) -> None:
    sentences = [entry.sentence for node in nodes for entry in node.crafts]
    if [source.id for source in sources] != cited_source_ids(sentences):
        raise ValueError("shared science lists every cited source once, in order of first citation")
