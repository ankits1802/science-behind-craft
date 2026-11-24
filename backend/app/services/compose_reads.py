from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.data.specimen_records import craft_specimens, stated_specimens
from app.models import Compound, CuratedClaim, CuratedCraft, Material, ProcessStage, Reaction, StageMaterial
from app.research.component_specs_general_delivery import UNIT_TEXT_MAX
from app.research.vocabulary import FACT_LEVELS

from . import knowledge_view
from .compose_held import (
    CraftHeld,
    HeldAfter,
    HeldCompound,
    HeldFact,
    HeldMaterial,
    HeldReaction,
    HeldSpecies,
    HeldStage,
    HeldTiming,
)
from .curated_index import CuratedPage, IndexMaterial, IndexReaction, IndexStage, stored_curated_page

__all__ = ["UNKNOWN_CRAFT", "craft_held"]

UNKNOWN_CRAFT = "No craft has the slug {slug!r}; find_crafts gives the slugs of crafts and families."


async def craft_held(session: AsyncSession, slug: str) -> CraftHeld | None:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise InvalidInput(UNKNOWN_CRAFT.format(slug=slug))
    stored = await session.scalar(select(CuratedCraft.page).where(CuratedCraft.craftId == craft.id))
    page = stored_curated_page(craft.id, stored)
    if page is None:
        return None
    marked = select(CuratedClaim.claimId, CuratedClaim.key).where(CuratedClaim.craftId == craft.id)
    owned = {row.claimId: row.key for row in (await session.execute(marked)).all()}
    stages = await _stage_rows(session, page)
    compounds = await _compounds(session, page)
    balance = await _balance(session, page)
    tokens = craft_specimens(craft.slug)
    stated = stated_specimens(craft.slug)
    colours = {claim: stated[key] for claim, key in owned.items() if key in stated}
    return CraftHeld(
        slug=craft.slug,
        name=craft.name,
        facts=await _facts(session, set(owned) & _referenced(page)),
        stages=tuple(_stage(entry, stages, page, colours) for entry in _ordered(page.stages)),
        materials=tuple(_material(entry, compounds, tokens.get(entry.key, ())) for entry in page.materials),
        reactions=tuple(_reaction(entry, balance) for entry in page.reactions),
    )


async def _facts(session: AsyncSession, wanted: set[uuid.UUID]) -> dict[uuid.UUID, HeldFact]:
    views, _ = await knowledge_view.claims_by_id(session, sorted(wanted, key=str))
    return {
        claim: HeldFact(claim, view.text)
        for claim, view in views.items()
        if view.level in FACT_LEVELS and len(view.text) <= UNIT_TEXT_MAX
    }


async def _stage_rows(
    session: AsyncSession, page: CuratedPage
) -> dict[uuid.UUID, tuple[str, str, tuple[uuid.UUID, ...]]]:
    ids = [stage.stage_id for stage in page.stages]
    if not ids:
        return {}
    named = (
        await session.execute(
            select(ProcessStage.id, ProcessStage.name, ProcessStage.stageType).where(ProcessStage.id.in_(ids))
        )
    ).all()
    used = (
        await session.execute(
            select(StageMaterial.stageId, StageMaterial.materialId).where(StageMaterial.stageId.in_(ids))
        )
    ).all()
    materials: dict[uuid.UUID, list[uuid.UUID]] = {}
    for stage_id, material_id in used:
        materials.setdefault(stage_id, []).append(material_id)
    return {row.id: (row.name, row.stageType, tuple(materials.get(row.id, ()))) for row in named}


async def _compounds(session: AsyncSession, page: CuratedPage) -> dict[str, HeldCompound]:
    cids = {material.pubchem_cid for material in page.materials if material.pubchem_cid is not None}
    linked = (
        await session.execute(
            select(Material.id, Compound.pubchemCid, Compound.name, Compound.formula)
            .join(Compound, Compound.id == Material.compoundId)
            .where(Material.id.in_([material.material_id for material in page.materials]))
        )
    ).all()
    held = (
        (
            await session.execute(
                select(Compound.pubchemCid, Compound.name, Compound.formula).where(
                    Compound.pubchemCid.in_(cids)
                )
            )
        ).all()
        if cids
        else []
    )
    by_cid = {row.pubchemCid: HeldCompound(row.pubchemCid, row.name, row.formula) for row in held}
    by_material = {
        row.id: HeldCompound(row.pubchemCid, row.name, row.formula)
        for row in linked
        if row.pubchemCid is not None
    }
    return {
        material.key: found
        for material in page.materials
        if (found := _compound_of(material, by_cid, by_material)) is not None
    }


def _compound_of(
    material: IndexMaterial, by_cid: Mapping[int, HeldCompound], by_material: Mapping[uuid.UUID, HeldCompound]
) -> HeldCompound | None:
    if material.pubchem_cid is not None:
        return by_cid.get(material.pubchem_cid, HeldCompound(material.pubchem_cid, material.name))
    return by_material.get(material.material_id)


async def _balance(session: AsyncSession, page: CuratedPage) -> dict[uuid.UUID, tuple[int, ...]]:
    ids = [reaction.reaction_id for reaction in page.reactions if reaction.reaction_id is not None]
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(Reaction.id, Reaction.coefficients).where(
                Reaction.id.in_(ids), Reaction.balanced.is_(True)
            )
        )
    ).all()
    return {row.id: tuple(row.coefficients) for row in rows if row.coefficients}


def _referenced(page: CuratedPage) -> set[uuid.UUID]:
    found: set[uuid.UUID] = set()
    for stage in page.stages:
        found.update(stage.claim_ids)
        found.update(claim for claim in (_after_claim(stage), _duration_claim(stage)) if claim is not None)
    for material in page.materials:
        found.update([*material.claim_ids, *(alternative.claim_id for alternative in material.alternatives)])
    for reaction in page.reactions:
        found.update(reaction.claim_ids)
    return found


def _after_claim(stage: IndexStage) -> uuid.UUID | None:
    return stage.after.claim_id if stage.after is not None else None


def _duration_claim(stage: IndexStage) -> uuid.UUID | None:
    return stage.duration.claim_id if stage.duration is not None else None


def _ordered(stages: Iterable[IndexStage]) -> list[IndexStage]:
    ranked = sorted(enumerate(stages), key=lambda pair: (pair[1].order is None, pair[1].order or 0, pair[0]))
    return [stage for _, stage in ranked]


def _stage(
    entry: IndexStage,
    rows: Mapping[uuid.UUID, tuple[str, str, tuple[uuid.UUID, ...]]],
    page: CuratedPage,
    colours: Mapping[uuid.UUID, tuple[str, ...]],
) -> HeldStage:
    name, stage_type, material_ids = rows.get(entry.stage_id, (entry.local_name or entry.key, "OTHER", ()))
    keys = {material.material_id: material.key for material in page.materials}
    return HeldStage(
        key=entry.key,
        name=name,
        stage_type=stage_type,
        claim_ids=tuple(entry.claim_ids),
        material_keys=tuple(keys[found] for found in material_ids if found in keys),
        after=None
        if entry.after is None
        else HeldAfter(
            entry.after.text,
            tuple(entry.after.colours),
            entry.after.claim_id,
            colours.get(entry.after.claim_id, ()),
        ),
        duration=None if entry.duration is None else HeldTiming(entry.duration.text, entry.duration.claim_id),
    )


def _material(
    entry: IndexMaterial, compounds: Mapping[str, HeldCompound], tokens: tuple[str, ...]
) -> HeldMaterial:
    return HeldMaterial(
        key=entry.key,
        name=entry.name,
        kind=entry.kind,
        claim_ids=tuple(entry.claim_ids),
        compound=compounds.get(entry.key),
        tokens=tokens,
        alternatives=tuple((alternative.key, alternative.claim_id) for alternative in entry.alternatives),
        role=entry.role,
        local_names=tuple(entry.local_names),
        botanical_name=entry.botanical_name,
    )


def _reaction(entry: IndexReaction, balance: Mapping[uuid.UUID, tuple[int, ...]]) -> HeldReaction:
    return HeldReaction(
        key=entry.key,
        kind=entry.kind,
        stage_key=entry.stage_key,
        reactants=tuple(HeldSpecies(species.name, species.formula) for species in entry.reactants),
        products=tuple(HeldSpecies(species.name, species.formula) for species in entry.products),
        claim_ids=tuple(entry.claim_ids),
        coefficients=balance.get(entry.reaction_id) if entry.reaction_id is not None else None,
    )
