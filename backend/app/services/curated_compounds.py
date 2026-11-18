from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_master_loader import ID_NAMESPACE
from app.data.craft_text import fold
from app.models import Compound, Source
from app.sources.reference.pubchem import PUBCHEM_LICENCE, PUBCHEM_PUBLISHER, compound_url

from .compound_lookup import record_source_id
from .curated_index import IndexMaterial
from .curation_writes import insert_missing

__all__ = [
    "CURATED_COMPOUND_ORIGIN",
    "CompoundPlan",
    "LinkedCompounds",
    "curated_compound_id",
    "curated_compounds",
    "linked_compounds",
]

CURATED_COMPOUND_ORIGIN = "IMPORT"


@dataclass(frozen=True)
class CompoundPlan:
    compounds: tuple[dict[str, Any], ...] = ()
    sources: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class LinkedCompounds:
    by_material: Mapping[uuid.UUID, uuid.UUID]
    written: int


def curated_compound_id(cid: int) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"curated-compound:{cid}")


def curated_compounds(
    materials: Sequence[IndexMaterial],
    *,
    stored_cids: Collection[int],
    stored_sources: Mapping[int, uuid.UUID],
    retrieved_at: datetime,
    unlinked_names: Collection[str] = (),
) -> CompoundPlan:
    names: dict[int, str] = {}
    for item in materials:
        if item.pubchem_cid and item.pubchem_cid not in stored_cids and fold(item.name) not in unlinked_names:
            names.setdefault(item.pubchem_cid, item.name)
    compounds = tuple(
        {
            "id": curated_compound_id(cid),
            "pubchemCid": cid,
            "name": name,
            "formula": None,
            "sourceId": stored_sources.get(cid, record_source_id(cid)),
        }
        for cid, name in names.items()
    )
    sources = tuple(
        _record_source(cid, name, retrieved_at) for cid, name in names.items() if cid not in stored_sources
    )
    return CompoundPlan(compounds=compounds, sources=sources)


async def linked_compounds(
    session: AsyncSession, materials: Sequence[IndexMaterial], *, retrieved_at: datetime
) -> LinkedCompounds:
    cids = sorted({item.pubchem_cid for item in materials if item.pubchem_cid})
    if not cids:
        return LinkedCompounds(by_material={}, written=0)
    stored = await _stored_compounds(session, cids)
    unlinked = await _unlinked_by_name(session, [item.name for item in materials if item.pubchem_cid])
    plan = curated_compounds(
        materials,
        stored_cids=stored,
        stored_sources=await _stored_sources(session, cids),
        retrieved_at=retrieved_at,
        unlinked_names=unlinked,
    )
    written = await insert_missing(session, Source, list(plan.sources))
    written += await insert_missing(session, Compound, list(plan.compounds))
    by_cid = await _stored_compounds(session, cids) if plan.compounds else stored
    return LinkedCompounds(by_material=_by_material(materials, by_cid, unlinked), written=written)


def _by_material(
    materials: Sequence[IndexMaterial], by_cid: Mapping[int, uuid.UUID], unlinked: Mapping[str, uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    linked: dict[uuid.UUID, uuid.UUID] = {}
    for item in materials:
        found = by_cid.get(item.pubchem_cid or 0) or (
            unlinked.get(fold(item.name)) if item.pubchem_cid else None
        )
        if found is not None:
            linked[item.material_id] = found
    return linked


def _record_source(cid: int, name: str, retrieved_at: datetime) -> dict[str, Any]:
    return {
        "id": record_source_id(cid),
        "kind": "COMPOUND_RECORD",
        "title": f"{name} (PubChem CID {cid})",
        "authors": [],
        "url": compound_url(cid),
        "publisher": PUBCHEM_PUBLISHER,
        "licence": PUBCHEM_LICENCE,
        "attribution": f"PubChem, {PUBCHEM_PUBLISHER}, CID {cid}",
        "reliability": "A",
        "storage": "LINK_ONLY",
        "retrievedAt": retrieved_at,
        "origin": CURATED_COMPOUND_ORIGIN,
        "externalIds": {"pubchem_cid": str(cid)},
    }


async def _stored_compounds(session: AsyncSession, cids: Sequence[int]) -> dict[int, uuid.UUID]:
    rows = await session.execute(
        select(Compound.pubchemCid, Compound.id).where(Compound.pubchemCid.in_(cids))
    )
    return {int(cid): compound_id for cid, compound_id in rows.tuples() if cid is not None}


async def _unlinked_by_name(session: AsyncSession, names: Sequence[str]) -> dict[str, uuid.UUID]:
    wanted = {fold(name) for name in names}
    rows = await session.execute(
        select(Compound.name, Compound.id)
        .where(Compound.pubchemCid.is_(None))
        .order_by(Compound.name, Compound.id)
    )
    found: dict[str, uuid.UUID] = {}
    for name, compound_id in rows.tuples():
        if fold(name) in wanted:
            found.setdefault(fold(name), compound_id)
    return found


async def _stored_sources(session: AsyncSession, cids: Sequence[int]) -> dict[int, uuid.UUID]:
    urls = {compound_url(cid): cid for cid in cids}
    rows = await session.execute(select(Source.url, Source.id).where(Source.url.in_(list(urls))))
    found: dict[int, uuid.UUID] = {}
    for url, source_id in rows.tuples():
        found.setdefault(urls[url], source_id)
    return found
