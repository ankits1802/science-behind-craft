from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping

from app.data.curation_scopes import CategoryScope, CraftScope

from .dossier import CATEGORY_SCOPE, Dossier
from .limits import DISCIPLINE_CLAIMS_MIN
from .problems import Problem

__all__ = ["FAMILY_SCOPE", "category_problems", "craft_scope_problems", "scope_header_problems"]

FAMILY_SCOPE = "FAMILY"
CRAFT_SCOPE = "CRAFT"


def scope_header_problems(
    dossier: Dossier, crafts: Mapping[str, CraftScope], categories: Mapping[str, CategoryScope]
) -> list[Problem]:
    if dossier.scope == CATEGORY_SCOPE:
        if dossier.slug in categories:
            return []
        return [Problem("categorySlug", f"{dossier.slug} is not a categorySlug of the master list")]
    craft = crafts.get(dossier.slug)
    if craft is None:
        return [
            Problem("craftSlug", f"{dossier.slug} is not on the master list or the portal craft register")
        ]
    if craft.merged_into is not None:
        return [
            Problem(
                "craftSlug", f"{dossier.slug} is merged into {craft.merged_into}; curate {craft.merged_into}"
            )
        ]
    wanted = FAMILY_SCOPE if craft.family else CRAFT_SCOPE
    if dossier.scope != wanted:
        return [Problem("scope", f"{dossier.slug} is a {_kind(craft)}; its scope is {wanted}")]
    return []


def craft_scope_problems(dossier: Dossier) -> list[Problem]:
    found = [
        Problem(where, "only a category dossier names sub-categories or member crafts")
        for where, sub_categories, crafts in _references(dossier)
        if sub_categories or crafts
    ]
    if dossier.scope == FAMILY_SCOPE and dossier.market.gi is not None:
        found.append(Problem("market.gi", "a family craft has no GI record; a GI names one craft"))
    return found


def category_problems(
    dossier: Dossier, category: CategoryScope, crafts: Mapping[str, CraftScope]
) -> list[Problem]:
    subs = {sub.slug: sub.name for sub in category.sub_categories}
    members = {
        slug
        for slug, craft in crafts.items()
        if craft.category_slug == category.slug and not craft.merged_into
    }
    found = (
        []
        if dossier.market.gi is None
        else [Problem("market.gi", "a category has no GI record; a GI names one craft")]
    )
    named: set[str] = set()
    for where, sub_categories, member_crafts in _references(dossier):
        named.update(sub_categories)
        found += [
            Problem(where, f"{slug} is not a sub-category of {category.slug}")
            for slug in sub_categories
            if slug not in subs
        ]
        found += [
            Problem(where, f"{slug} is not a member craft of {category.slug}")
            for slug in member_crafts
            if slug not in members
        ]
    found += [
        Problem(
            "overview",
            f"sub-category {slug} ({name}) has no overview sentence and no open question; cite one, "
            "or ask an open question saying no source was found",
        )
        for slug, name in subs.items()
        if slug not in named
    ]
    return found + _section_problems(dossier)


def _section_problems(dossier: Dossier) -> list[Problem]:
    counts = Counter(claim.discipline for claim in dossier.claims if not claim.hypothesis)
    sections = {section.discipline for section in dossier.overview.sections}
    return [
        Problem("overview", f"{discipline} has {count} claims and no section; the sources support one")
        for discipline, count in counts.items()
        if count >= DISCIPLINE_CLAIMS_MIN and discipline not in sections
    ]


def _references(dossier: Dossier) -> Iterator[tuple[str, list[str], list[str]]]:
    for where, sentence in dossier.overview.located_sentences():
        yield where, sentence.sub_categories, sentence.crafts
    for question in dossier.open_questions:
        yield question.id, question.sub_categories, []


def _kind(craft: CraftScope) -> str:
    return "family craft (catch-all or practised across India)" if craft.family else "single named craft"
