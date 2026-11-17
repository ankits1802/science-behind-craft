from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Sequence
from itertools import batched
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.data.craft_master_loader import CRAFT_WIKIDATA_FILE, ID_NAMESPACE
from app.models import Concept, Craft, CraftAlias, Term, TermConcept, TermCraft
from app.research.subject_keys import term_key
from app.research.term_marking import GlossaryEntry

from .claim_seed import load_seed_claims, seed_id
from .glossary_plan import CraftNames, TermSeed, compounds_of, concepts_of, glossary_plan, wikidata_links
from .science_seed import load_science_seed

__all__ = ["LATIN_SCRIPT", "glossary_entries", "glossary_seed", "seed_terms", "term_id"]

BATCH = 500
LATIN_SCRIPT = "Latn"
ACTIVE = "ACTIVE"
MERGED = "MERGED"
TERM_SEEDED_COLUMNS = ("label", "meaning", "localNames", "aliases", "wikidataId")


def term_id(key: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"term:{key}")


def glossary_seed(crafts: Sequence[CraftNames]) -> list[TermSeed]:
    wikidata = wikidata_links(json.loads(CRAFT_WIKIDATA_FILE.read_text(encoding="utf-8")))
    return glossary_plan(crafts, wikidata, concepts_of(load_seed_claims()), compounds_of(load_science_seed()))


async def seed_terms(session: AsyncSession) -> dict[str, int]:
    craft_ids, crafts = await _craft_names(session)
    plan = glossary_seed(crafts)
    present = await _present_concepts(
        session, [seed_id("concept", k) for seed in plan for k in seed.concept_keys]
    )
    await _upsert_terms(session, plan)
    stored = await _stored_ids(session, [seed.key for seed in plan])
    craft_links = [
        {"termId": stored[seed.key], "craftId": craft_ids[slug]}
        for seed in plan
        for slug in seed.craft_slugs
        if slug in craft_ids
    ]
    concept_links = [
        {"termId": stored[seed.key], "conceptId": seed_id("concept", key)}
        for seed in plan
        for key in seed.concept_keys
        if seed_id("concept", key) in present
    ]
    linked = await _insert_links(session, TermCraft, craft_links)
    linked += await _insert_links(session, TermConcept, concept_links)
    await session.flush()
    return {
        "terms": len(plan),
        "craftLinks": len(craft_links),
        "conceptLinks": len(concept_links),
        "newLinks": linked,
    }


async def _upsert_terms(session: AsyncSession, plan: Sequence[TermSeed]) -> None:
    for chunk in batched(plan, BATCH, strict=False):
        statement = insert(Term).values([_term_values(seed) for seed in chunk])
        changed = {column: statement.excluded[column] for column in TERM_SEEDED_COLUMNS}
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[Term.key], set_={**changed, "updatedAt": func.now()}
            )
        )


async def glossary_entries(session: AsyncSession, craft_ids: Sequence[uuid.UUID]) -> list[GlossaryEntry]:
    if not craft_ids:
        return []
    names = await session.scalars(select(Craft.name).where(Craft.id.in_(craft_ids)))
    own = {_key_of(name) for name in names}
    linked = select(TermCraft.termId).where(TermCraft.craftId.in_(craft_ids))
    rows = await session.scalars(select(Term).where(Term.id.in_(linked)).order_by(Term.key))
    return [
        GlossaryEntry(key=row.key, surfaces=(row.label, *row.aliases, *row.localNames))
        for row in rows
        if row.key not in own
    ]


async def _craft_names(session: AsyncSession) -> tuple[dict[str, uuid.UUID], list[CraftNames]]:
    crafts = (
        await session.execute(select(Craft.id, Craft.slug, Craft.name).where(Craft.status != MERGED))
    ).all()
    aliases: dict[uuid.UUID, list[Any]] = {}
    rows = await session.execute(
        select(CraftAlias.craftId, CraftAlias.alias, CraftAlias.script)
        .where(CraftAlias.status == ACTIVE)
        .order_by(CraftAlias.craftId, CraftAlias.alias)
    )
    for row in rows:
        aliases.setdefault(row.craftId, []).append(row)
    names = [
        CraftNames(
            slug=craft.slug,
            name=craft.name,
            aliases=tuple(a.alias for a in aliases.get(craft.id, []) if a.script in (None, LATIN_SCRIPT)),
            local_names=tuple(
                a.alias for a in aliases.get(craft.id, []) if a.script not in (None, LATIN_SCRIPT)
            ),
        )
        for craft in crafts
    ]
    return {craft.slug: craft.id for craft in crafts}, names


async def _present_concepts(session: AsyncSession, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    wanted = list(dict.fromkeys(ids))
    found: set[uuid.UUID] = set()
    for chunk in batched(wanted, BATCH, strict=False):
        found.update(await session.scalars(select(Concept.id).where(Concept.id.in_(chunk))))
    return found


async def _stored_ids(session: AsyncSession, keys: Sequence[str]) -> dict[str, uuid.UUID]:
    stored: dict[str, uuid.UUID] = {}
    for chunk in batched(keys, BATCH, strict=False):
        stored.update(
            (await session.execute(select(Term.key, Term.id).where(Term.key.in_(chunk)))).tuples().all()
        )
    return stored


async def _insert_links(session: AsyncSession, model: Any, rows: list[dict[str, uuid.UUID]]) -> int:
    inserted = 0
    for chunk in batched(rows, BATCH, strict=False):
        result = await session.execute(
            insert(model).values(list(chunk)).on_conflict_do_nothing().returning(model.termId)
        )
        inserted += len(result.scalars().all())
    return inserted


def _key_of(name: str) -> str | None:
    try:
        return term_key(name)
    except InvalidInput:
        return None


def _term_values(seed: TermSeed) -> dict[str, Any]:
    return {
        "id": term_id(seed.key),
        "key": seed.key,
        "label": seed.label,
        "meaning": seed.meaning,
        "localNames": seed.local_names,
        "aliases": seed.aliases,
        "wikidataId": seed.wikidata_id,
    }
