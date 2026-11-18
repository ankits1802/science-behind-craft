from __future__ import annotations

from app.data.craft_families import load_craft_families
from app.research.citations import Citation
from app.research.craft_page import PageClaim, PageCraft, SubjectRef

from .category_page import CategoryPageRecords
from .chapter_context import FamilyScience

__all__ = ["family_science", "family_slug"]

CURATED = "CURATED"
CATEGORY_PATH = "/categories/{slug}"


def family_slug(craft: PageCraft) -> str | None:
    if craft.category_name is None:
        return None
    return load_craft_families().category_slugs.get(craft.category_name)


def family_science(records: CategoryPageRecords, craft: PageCraft) -> FamilyScience | None:
    if records.curated is None:
        return None
    category = records.category
    claims = []
    for view in records.views:
        facts = records.facts.get(view.id)
        if facts is None:
            continue
        claims.append(
            PageClaim(
                id=view.id,
                text=view.text,
                level=view.level,
                discipline=facts.discipline,
                subject=SubjectRef(id=None, name=category.label, kind="CONCEPT"),
                provenance=CURATED,
                sources_differ=facts.sources_differ,
                citations=[Citation.model_validate(citation) for citation in view.citations],
            )
        )
    return FamilyScience(
        slug=category.slug,
        label=craft.family_label or category.label,
        path=CATEGORY_PATH.format(slug=category.slug),
        index=records.curated,
        claims=tuple(claims),
        sources=dict(records.sources),
    )
