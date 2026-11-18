from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .craft_master_loader import DATA_DIR, MasterCraft, load_master

__all__ = [
    "CRAFT_FAMILIES_FILE",
    "CRAFT_FAMILIES_VERSION",
    "CRAFT_PLACEHOLDER",
    "FAMILY_PALETTES",
    "PLACEHOLDER_LEADS",
    "PRONOUNS",
    "QUESTIONS_PER_KIND",
    "CraftFamilies",
    "CraftFamily",
    "CraftKind",
    "FamilyPlace",
    "load_craft_families",
    "parse_craft_families",
]

CRAFT_FAMILIES_FILE = DATA_DIR / "craft_families.json"
CRAFT_FAMILIES_VERSION = 2
CRAFT_PLACEHOLDER = "{craft}"
QUESTIONS_PER_KIND = 3
PLACEHOLDER_LEADS = frozenset({"of", "for", "in", "into", "on", "make"})
PRONOUNS = frozenset({"it", "its", "itself", "they", "them", "their", "themselves"})
WORDS = re.compile(r"[^\W\d_]+")
FAMILY_PALETTES = ("indigo", "bronze", "sandstone", "teak", "hide", "cane", "terracotta", "paper", "lac")


@dataclass(frozen=True)
class CraftKind:
    slug: str
    label: str
    other_name: str
    questions: tuple[str, ...]
    other_questions: tuple[str, ...]


@dataclass(frozen=True)
class CraftFamily:
    slug: str
    label: str
    palette: str
    kinds: tuple[CraftKind, ...]


@dataclass(frozen=True)
class FamilyPlace:
    family: CraftFamily | None
    kind: CraftKind | None


@dataclass(frozen=True)
class CraftFamilies:
    default_questions: tuple[str, ...]
    families: tuple[CraftFamily, ...]
    category_slugs: Mapping[str, str]
    sub_category_slugs: Mapping[tuple[str, str], str]

    def family(self, slug: str | None) -> CraftFamily | None:
        return next((family for family in self.families if family.slug == slug), None)

    def kind(self, slug: str | None) -> CraftKind | None:
        return next((kind for family in self.families for kind in family.kinds if kind.slug == slug), None)

    def place_of(self, category_name: str | None, sub_category_name: str | None) -> FamilyPlace:
        names = (category_name or "", sub_category_name or "")
        return FamilyPlace(
            family=self.family(self.category_slugs.get(names[0])),
            kind=self.kind(self.sub_category_slugs.get(names)),
        )

    def questions(self, place: FamilyPlace, craft_name: str) -> list[str]:
        asked = place.kind.questions if place.kind is not None else self.default_questions
        return [question.replace(CRAFT_PLACEHOLDER, craft_name) for question in asked]


def parse_craft_families(raw: Mapping[str, Any], master: Sequence[MasterCraft]) -> CraftFamilies:
    if raw.get("version") != CRAFT_FAMILIES_VERSION:
        raise ValueError(f"craft families file is version {raw.get('version')}, not {CRAFT_FAMILIES_VERSION}")
    families = tuple(_family(row) for row in raw["families"])
    _unique([family.slug for family in families], "family")
    _unique([kind.slug for family in families for kind in family.kinds], "kind")
    _unique([family.palette for family in families], "family palette")
    return CraftFamilies(
        default_questions=_questions(raw["defaultQuestions"], "the default questions"),
        families=families,
        category_slugs={craft.category: craft.category_slug for craft in master},
        sub_category_slugs={
            (craft.category, craft.sub_category): craft.sub_category_slug for craft in master
        },
    )


@lru_cache(maxsize=1)
def load_craft_families(path: Path = CRAFT_FAMILIES_FILE) -> CraftFamilies:
    return parse_craft_families(json.loads(path.read_text(encoding="utf-8")), load_master())


def _family(row: Mapping[str, Any]) -> CraftFamily:
    return CraftFamily(
        slug=_text(row["slug"], "a family slug"),
        label=_text(row["label"], f"family {row['slug']}'s label"),
        palette=_palette(row["palette"], row["slug"]),
        kinds=tuple(_kind(kind) for kind in row["kinds"]),
    )


def _kind(row: Mapping[str, Any]) -> CraftKind:
    slug = _text(row["slug"], "a kind slug")
    return CraftKind(
        slug=slug,
        label=_text(row["label"], f"kind {slug}'s label"),
        other_name=_text(row["otherName"], f"kind {slug}'s other name"),
        questions=_questions(row["questions"], f"kind {slug}"),
        other_questions=_other_questions(row.get("otherQuestions"), f"kind {slug}'s catch-all row"),
    )


def _palette(value: Any, family: str) -> str:
    if value not in FAMILY_PALETTES:
        raise ValueError(f"family {family}'s palette {value!r} is not one of {', '.join(FAMILY_PALETTES)}")
    return value


def _questions(rows: Any, owner: str) -> tuple[str, ...]:
    asked = _three_questions(rows, owner)
    for question in asked:
        if question.count(CRAFT_PLACEHOLDER) != 1:
            raise ValueError(f"{owner}: {question!r} names {CRAFT_PLACEHOLDER} once")
        _agrees_with_any_name(question, owner)
    return tuple(asked)


def _other_questions(rows: Any, owner: str) -> tuple[str, ...]:
    asked = _three_questions(rows, owner)
    named = [question for question in asked if CRAFT_PLACEHOLDER in question]
    if named:
        raise ValueError(f"{owner}: {named[0]!r} asks about the kind, so it names no craft")
    return tuple(asked)


def _three_questions(rows: Any, owner: str) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError(f"{owner} lists no questions")
    if len(rows) != QUESTIONS_PER_KIND:
        raise ValueError(f"{owner} has {len(rows)} questions, not {QUESTIONS_PER_KIND}")
    for question in rows:
        if not isinstance(question, str) or not question.endswith("?") or question != question.strip():
            raise ValueError(f"{owner}: {question!r} is one question ending with a question mark")
    return rows


def _agrees_with_any_name(question: str, owner: str) -> None:
    before = WORDS.findall(question.split(CRAFT_PLACEHOLDER)[0].casefold())
    pronouns = PRONOUNS.intersection(WORDS.findall(question.casefold()))
    if not before or before[-1] not in PLACEHOLDER_LEADS or pronouns:
        leads = ", ".join(sorted(PLACEHOLDER_LEADS))
        raise ValueError(
            f"{owner}: {question!r} must read for a singular or plural name: {CRAFT_PLACEHOLDER} "
            f"comes after one of {leads} and no pronoun refers back to it"
        )


def _text(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{what} is non-empty text without outer spaces")
    return value


def _unique(slugs: Sequence[str], what: str) -> None:
    repeated = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if repeated:
        raise ValueError(f"each {what} is listed once; repeated: {', '.join(repeated)}")
