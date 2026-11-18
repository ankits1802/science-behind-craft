from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from app.core.errors import InvalidInput

from .subject_keys import topic_key

__all__ = ["FACET_NAMESPACES", "PLACE_FACETS", "TopicSubjects", "facet_topic", "facet_topics"]

FACET_NAMESPACES: Mapping[str, str] = MappingProxyType(
    {
        "OVERVIEW": "craft",
        "PROCESS": "process",
        "CHEMISTRY": "reaction",
        "PHYSICS": "concept",
        "MATERIALS": "material",
        "GEOGRAPHY": "water",
        "GEOLOGY": "soil",
        "CLIMATE": "climate",
        "ECOLOGY": "ecology",
        "BOTANY": "material",
        "HISTORY": "history",
        "ECONOMICS": "economy",
        "DESIGN": "design",
        "HEALTH": "health",
        "SOCIETY": "society",
        "POLICY": "policy",
    }
)
PLACE_FACETS = frozenset({"GEOGRAPHY", "GEOLOGY", "CLIMATE"})


@dataclass(frozen=True)
class TopicSubjects:
    craft_slug: str
    question_terms: tuple[str, ...] = ()
    districts: tuple[str, ...] = ()


def facet_topic(facet: str, subjects: TopicSubjects) -> str | None:
    if subjects.question_terms:
        chosen: Sequence[str] = subjects.question_terms
    elif facet in PLACE_FACETS and subjects.districts:
        chosen = subjects.districts
    else:
        chosen = (subjects.craft_slug,)
    try:
        return topic_key(FACET_NAMESPACES[facet], *chosen)
    except InvalidInput:
        return None


def facet_topics(facets: Sequence[str], subjects: TopicSubjects) -> dict[str, str]:
    found = {facet: facet_topic(facet, subjects) for facet in dict.fromkeys(facets)}
    return {facet: topic for facet, topic in found.items() if topic is not None}
