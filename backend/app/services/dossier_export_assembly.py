from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.curation.dossier import Dossier
from app.curation.entities import Place
from app.curation.parts import Search

from .curated_category_index import CuratedCategoryPage
from .curated_index import CuratedPage
from .curation_keys import curated_id
from .curation_rows import place_concept_keys
from .dossier_export_claims import ExportedEvidence, claim_keys, exported_evidence
from .dossier_export_market import stored_market
from .dossier_export_overview import ExportedOverview, same_curation, stored_overview
from .dossier_export_parts import (
    page_communities,
    page_conflicts,
    page_environment,
    page_glossary,
    page_materials,
    page_native_names,
    page_pictures,
    page_places,
    page_questions,
    page_reactions,
    page_stages,
    page_tools,
)
from .dossier_export_records import StoredCuration

__all__ = ["CATEGORY_KEPT_PARTS", "ExportedDossier", "exported_dossier"]

CATEGORY_KEPT_PARTS = ("places", "communities", "stages", "materials", "tools", "environment", "native_names")
CATEGORY_KEPT_NOTE = "kept as the dossier in git gives them: the category import does not store them"


@dataclass(frozen=True)
class ExportedDossier:
    dossier: Dossier
    carried: tuple[str, ...]
    failed_quotes: int


def exported_dossier(stored: StoredCuration, previous: Dossier | None) -> ExportedDossier:
    try:
        if isinstance(stored.page, CuratedCategoryPage):
            return _category(stored, stored.page, _category_guide(stored, previous))
        return _craft(stored, stored.page, previous)
    except ValidationError as error:
        raise InvalidInput(
            f"the stored record of {stored.slug} does not make a valid dossier: {error}"
        ) from error


def _craft(stored: StoredCuration, page: CuratedPage, previous: Dossier | None) -> ExportedDossier:
    keys = claim_keys(stored)
    places = page_places(page, keys)
    by_key = {place.id: place for place in places}
    choices: dict[uuid.UUID, list[Place]] = defaultdict(list)
    for place in page.places:
        choices[place.concept_id].append(by_key[place.key])
    evidence = exported_evidence(stored, previous, choices)
    overview = stored_overview(stored, keys, previous)
    parts: dict[str, Any] = {
        "craft_slug": stored.slug,
        "places": places,
        "communities": page_communities(page, keys),
        "stages": page_stages(stored, keys, previous),
        "materials": page_materials(page, keys),
        "tools": page_tools(page, keys),
        "reactions": page_reactions(page, keys),
        "environment": page_environment(page, keys),
        "market": stored_market(stored, keys, places, previous),
        "native_names": page_native_names(page, keys),
    }
    return _assembled(stored, parts, evidence, overview)


def _category(stored: StoredCuration, page: CuratedCategoryPage, previous: Dossier) -> ExportedDossier:
    groups = place_concept_keys(previous)
    choices: dict[uuid.UUID, list[Place]] = defaultdict(list)
    for place in previous.places:
        choices[curated_id(stored.slug, "concept", groups[place.id])].append(place)
    keys = claim_keys(stored)
    evidence = exported_evidence(stored, previous, choices)
    overview = stored_overview(stored, keys, previous)
    kept = {part: getattr(previous, part) for part in CATEGORY_KEPT_PARTS}
    stages = {reaction.id: reaction.stage_id for reaction in previous.reactions}
    parts: dict[str, Any] = {
        "category_slug": stored.slug,
        **kept,
        "reactions": page_reactions(page, keys, stages=stages),
        "market": previous.market,
    }
    named = [part for part in (*CATEGORY_KEPT_PARTS, "market") if getattr(previous, part) != _empty(part)]
    if any(stages.values()):
        named.append("the stages of reactions")
    notes = (f"{', '.join(named)}: {CATEGORY_KEPT_NOTE}",) if named else ()
    return _assembled(stored, parts, evidence, overview, notes=notes)


def _empty(part: str) -> Any:
    return Dossier.model_fields[part].get_default(call_default_factory=True)


def _category_guide(stored: StoredCuration, previous: Dossier | None) -> Dossier:
    if previous is None:
        raise InvalidInput(
            f"category {stored.slug} cannot be exported without its dossier in git: the category import "
            f"does not store its {', '.join(CATEGORY_KEPT_PARTS)} or market records"
        )
    if not same_curation(stored, previous):
        raise InvalidInput(
            f"the dossier of category {stored.slug} in git is version {previous.version}, the database holds "
            f"version {stored.page.version}; import or restore the version the database holds first"
        )
    return previous


def _assembled(
    stored: StoredCuration,
    parts: dict[str, Any],
    evidence: ExportedEvidence,
    overview: ExportedOverview,
    *,
    notes: tuple[str, ...] = (),
) -> ExportedDossier:
    page = stored.page
    keys = claim_keys(stored)
    dossier = Dossier(
        scope=stored.scope,
        version=page.version,
        curated_at=page.curated_at,
        coverage=page.coverage,
        searched=[Search(query=item.query, site=item.site) for item in page.searched],
        sources=evidence.sources,
        claims=evidence.claims,
        glossary=page_glossary(page, keys),
        conflicts=page_conflicts(page, keys),
        open_questions=page_questions(page, keys),
        pictures=page_pictures(page, stored.media, keys),
        overview=overview.overview,
        **parts,
    )
    carried = (*notes, *evidence.carried, *overview.carried)
    return ExportedDossier(dossier=dossier, carried=carried, failed_quotes=evidence.failed_quotes)
