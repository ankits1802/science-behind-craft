from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app.core.errors import InvalidInput
from app.curation.check_file import CheckFile
from app.curation.checks import default_context
from app.curation.dossier import Dossier
from app.curation.files import checked_dossier
from app.models import MediaRef as MediaRefRow
from app.research.category_page import CategoryList, CategoryPage
from app.research.citations import SourceRef

from .answer_events import cited_claims
from .category_page import CategoryClaimFacts, CategoryPageRecords, category_list, category_page
from .category_plan import CategoryTarget, category_plan
from .category_register import CategoryRecord, register_categories
from .curated_category_index import indexed_category_overview
from .curation_overview import overview_pieces
from .curation_preview import plan_views
from .knowledge_view import source_ref
from .media_ref_store import stored_media_ref

__all__ = ["category_list_preview", "category_page_preview", "preview_category_records"]


def category_page_preview(slug: str, *, dossier: Path | None = None) -> CategoryPage:
    category = _registered(slug)
    if dossier is None:
        return category_page(CategoryPageRecords(category=category))
    checked, check = _checked(dossier)
    if checked.slug != slug:
        raise InvalidInput(f"{dossier.name} is the dossier of {checked.slug}, not of {slug}")
    return category_page(preview_category_records(checked, check, category))


def category_list_preview(dossiers: Sequence[Path] = ()) -> CategoryList:
    by_slug = {dossier.slug: (dossier, check) for dossier, check in map(_checked, dossiers)}
    records = [
        preview_category_records(*by_slug[category.slug], category)
        if category.slug in by_slug
        else CategoryPageRecords(category=category)
        for category in register_categories()
    ]
    return category_list(records)


def preview_category_records(
    dossier: Dossier, check: CheckFile, category: CategoryRecord
) -> CategoryPageRecords:
    plan = category_plan(
        dossier, check, CategoryTarget(id=category.id, slug=category.slug, name=category.name)
    )
    views, sources = plan_views(plan)
    overview = overview_pieces(
        dossier, cited_claims(list(views.values()), sources), craft_id=None, districts=()
    )
    differ = {row["id"]: row["sourcesDiffer"] for row in plan.part("claims")}
    facts = {
        row["claimId"]: CategoryClaimFacts(
            discipline=row["discipline"], sources_differ=differ[row["claimId"]]
        )
        for row in plan.part("curatedClaims")
    }
    return CategoryPageRecords(
        category=category,
        curated=indexed_category_overview(plan.index, overview),
        views=tuple(views.values()),
        facts=facts,
        sources={str(key): SourceRef.model_validate(source_ref(row)) for key, row in sources.items()},
        pieces={piece.id: piece for piece in overview.pieces},
        media={row["id"]: stored_media_ref(MediaRefRow(**row)) for row in plan.part("media")},
    )


def _registered(slug: str) -> CategoryRecord:
    found = next((category for category in register_categories() if category.slug == slug), None)
    if found is None:
        raise InvalidInput(f"{slug} is not a category of the master list")
    return found


def _checked(path: Path) -> tuple[Dossier, CheckFile]:
    result = checked_dossier(path, default_context())
    if result.problems or result.dossier is None or result.check is None:
        lines = (
            "; ".join(problem.line(path.name) for problem in result.problems) or "the check file is missing"
        )
        raise InvalidInput(f"{path.name} does not pass its checks: {lines}")
    return result.dossier, result.check
