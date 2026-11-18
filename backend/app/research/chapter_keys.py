from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

__all__ = [
    "CHAPTER_KEYS",
    "CHAPTER_TITLES",
    "DISCIPLINE_CHAPTERS",
    "PICTURE_PLACEMENTS",
    "PLACED_ONCE_PER_CHAPTER",
    "PLACED_ONCE_PER_PAGE",
    "PLACEMENT_NEEDS_MATERIAL",
    "PLACEMENT_NEEDS_STAGE",
]

CHAPTER_KEYS = ("glance", "made", "chem", "why", "history", "market", "whatif", "people", "kin", "sources")
CHAPTER_TITLES: Mapping[str, str] = MappingProxyType(
    {
        "glance": "At a glance",
        "made": "How it is made",
        "chem": "The chemistry",
        "why": "Why {place}",
        "history": "History and trade",
        "market": "Market and GI",
        "whatif": "What if",
        "people": "People and voices",
        "kin": "Kin crafts and shared science",
        "sources": "Sources",
    }
)
DISCIPLINE_CHAPTERS: Mapping[str, str] = MappingProxyType(
    {
        "OVERVIEW": "glance",
        "DESIGN": "glance",
        "PROCESS": "made",
        "HEALTH": "made",
        "CHEMISTRY": "chem",
        "PHYSICS": "chem",
        "MATERIALS": "chem",
        "BOTANY": "chem",
        "GEOGRAPHY": "why",
        "GEOLOGY": "why",
        "CLIMATE": "why",
        "ECOLOGY": "why",
        "HISTORY": "history",
        "ECONOMICS": "market",
    }
)
PICTURE_PLACEMENTS = ("MASTHEAD", "OPENER", "PLATE", "RECORD", "STAGE", "MATERIAL")
PLACED_ONCE_PER_PAGE = frozenset({"MASTHEAD"})
PLACED_ONCE_PER_CHAPTER = frozenset({"OPENER"})
PLACEMENT_NEEDS_STAGE = frozenset({"STAGE"})
PLACEMENT_NEEDS_MATERIAL = frozenset({"MATERIAL"})
