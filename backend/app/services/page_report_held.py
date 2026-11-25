from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.page_report_drawable import HeldChange, HeldShapes

from .compose_components import COMPOSED_KINDS, ComposeDeps
from .compose_held import CraftHeld, HeldReaction
from .compose_parts import joined

__all__ = ["HELD_SUBJECT", "held_shapes", "shapes_of"]

HELD_SUBJECT = "craft"


async def held_shapes(
    session: AsyncSession, deps: ComposeDeps, subject_kind: str, slug: str
) -> HeldShapes | None:
    if subject_kind != HELD_SUBJECT:
        return None
    held = await deps.held(session, slug)
    return None if held is None else shapes_of(held)


def shapes_of(held: CraftHeld) -> HeldShapes:
    reactions = tuple(
        HeldChange(reaction.key, _said(reaction), _ids(held.stated(reaction.claim_ids)))
        for reaction in held.reactions
        if reaction.balanced() and held.stated(reaction.claim_ids)
    )
    stages = tuple(
        HeldChange(stage.key, stage.name, _ids(held.stated(stage.claim_ids)))
        for stage in held.stages
        if held.stated(stage.claim_ids)
    )
    return HeldShapes(reactions=reactions, stages=stages, composers=COMPOSED_KINDS)


def _said(reaction: HeldReaction) -> str:
    sides = [joined([species.name for species in side]) for side in (reaction.reactants, reaction.products)]
    return f"{sides[0]} to {sides[1]}"


def _ids(claims: Iterable[uuid.UUID]) -> tuple[str, ...]:
    return tuple(str(claim) for claim in claims)
