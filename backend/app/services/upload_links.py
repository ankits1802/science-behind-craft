from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import token_matches_user
from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.core.security import TOKEN_VERSION_CLAIM
from app.models import Craft, ImageContribution, Process, ProcessStage, UploadLink, User
from app.research.image_contributions import ImageDeclaration
from app.research.retrieval import OPEN_CHUNK_ACLS
from app.research.upload_links import (
    LINK_PREFIX,
    OPEN,
    OPEN_LINKS_MAX,
    SLOT_PREFIX,
    UPLOAD_LINK_LIFETIME,
    USED,
    SlotCraft,
    SlotDeclaration,
    SlotFact,
    SlotStage,
    UploadLinkView,
    UploadSlot,
    declared,
    link_state,
)

from . import image_contributions as images, knowledge_view
from .oauth_tokens import new_secret, stored_secret
from .object_store import ObjectStore

__all__ = [
    "IssuedLink",
    "LinkGone",
    "LinkRefused",
    "Picture",
    "UnknownLink",
    "fill_by_link",
    "fill_slot",
    "link_view",
    "renew_link",
    "start_upload",
]

NEEDS_PROPOSER = "Giving pictures needs an account of Researcher or above."
TOO_MANY = f"This account holds {OPEN_LINKS_MAX} open upload links. Use one, or wait for them to expire."
USED_DETAIL = "This upload link was used already. Ask for a new one."
EXPIRED_DETAIL = "This upload link has expired. Ask for a new one."
STILL_OPEN = "This upload link still works. Use it."
ACCOUNT_CHANGED = "This upload link no longer works: its account signed out or changed. Ask for a new one."
NO_CRAFT = "No craft has the slug {slug}"
NO_STAGE = "That stage is not one of this craft's"
NO_FACT = "No shown fact has the id {claim_id}"


class UnknownLink(Exception):
    pass


class LinkGone(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class LinkRefused(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class IssuedLink:
    link_token: str
    slot_token: str | None
    expires_at: datetime
    craft: SlotCraft
    stage: SlotStage | None
    facts: list[SlotFact]


@dataclass(frozen=True)
class Picture:
    declaration: SlotDeclaration
    data: bytes


async def start_upload(
    session: AsyncSession,
    user: User,
    slot: UploadSlot,
    declaration: SlotDeclaration | None,
    *,
    now: datetime,
) -> IssuedLink:
    if not can(user, Capability.PROPOSE_KNOWLEDGE):
        raise InvalidInput(NEEDS_PROPOSER)
    if declaration is not None:
        _checked(slot, declaration)
    await _refuse_too_many(session, user.id, now)
    craft = await _craft(session, slot.craft_slug)
    stage = await _stage(session, craft.id, slot.stage_id)
    facts = await _facts(session, slot.claim_ids)
    link = new_secret(LINK_PREFIX)
    slot_token = None if declaration is None else new_secret(SLOT_PREFIX)
    row = UploadLink(
        userId=user.id,
        userTokenVersion=int(user.tokenVersion or 0),
        craftId=craft.id,
        stageId=slot.stage_id,
        claimIds=list(slot.claim_ids),
        linkHash=_digest(link, LINK_PREFIX),
        slotHash=None if slot_token is None else _digest(slot_token, SLOT_PREFIX),
        declaration=None if declaration is None else declaration.model_dump(mode="json", by_alias=True),
        expiresAt=now + UPLOAD_LINK_LIFETIME,
        createdAt=now,
    )
    session.add(row)
    await session.flush()
    shown = SlotCraft(slug=craft.slug, name=craft.name)
    return IssuedLink(link, slot_token, row.expiresAt, shown, stage, facts)


async def link_view(session: AsyncSession, user: User, token: str, *, now: datetime) -> UploadLinkView:
    row = await _own_link(session, user, token, lock=False)
    craft = await session.get(Craft, row.craftId)
    if craft is None:
        raise UnknownLink(token)
    return UploadLinkView(
        state=link_state(used_at=row.usedAt, expires_at=row.expiresAt, now=now),
        craft=SlotCraft(slug=craft.slug, name=craft.name),
        stage=await _stage(session, row.craftId, row.stageId),
        facts=await _shown_facts(session, list(row.claimIds)),
        expires_at=row.expiresAt,
        contribution_id=row.contributionId,
    )


async def renew_link(session: AsyncSession, user: User, token: str, *, now: datetime) -> IssuedLink:
    row = await _own_link(session, user, token, lock=True)
    if link_state(used_at=row.usedAt, expires_at=row.expiresAt, now=now) == OPEN:
        raise LinkRefused(STILL_OPEN)
    craft = await session.get(Craft, row.craftId)
    if craft is None:
        raise UnknownLink(token)
    slot = UploadSlot(craft_slug=craft.slug, stage_id=row.stageId, claim_ids=list(row.claimIds))
    return await start_upload(session, user, slot, None, now=now)


async def fill_by_link(
    session: AsyncSession, user: User, token: str, picture: Picture, *, objects: ObjectStore, now: datetime
) -> ImageContribution:
    row = await _own_link(session, user, token, lock=True)
    return await _fill(session, row, user, picture, objects=objects, now=now)


async def fill_slot(
    session: AsyncSession, token: str, data: bytes, *, objects: ObjectStore, now: datetime
) -> ImageContribution:
    digest = stored_secret(token, SLOT_PREFIX)
    row = None if digest is None else await _locked(session, UploadLink.slotHash == digest)
    if row is None or row.declaration is None:
        raise UnknownLink(token)
    _require_open(row, now)
    user = await session.get(User, row.userId)
    if user is None or not _owner_live(row, user) or not can(user, Capability.PROPOSE_KNOWLEDGE):
        raise LinkGone(ACCOUNT_CHANGED)
    picture = Picture(declaration=SlotDeclaration.model_validate(row.declaration), data=data)
    return await _fill(session, row, user, picture, objects=objects, now=now)


async def _fill(
    session: AsyncSession,
    row: UploadLink,
    user: User,
    picture: Picture,
    *,
    objects: ObjectStore,
    now: datetime,
) -> ImageContribution:
    _require_open(row, now)
    craft = await session.get(Craft, row.craftId)
    if craft is None:
        raise UnknownLink(str(row.id))
    slot = UploadSlot(craft_slug=craft.slug, stage_id=row.stageId, claim_ids=list(row.claimIds))
    contribution = await images.declare(session, user, _checked(slot, picture.declaration), now=now)
    upload = images.Upload(contribution_id=contribution.id, user=user, data=picture.data)
    received = await images.receive_file(session, upload, objects=objects, now=now)
    row.usedAt, row.contributionId = now, received.id
    await session.flush()
    return received


def _checked(slot: UploadSlot, declaration: SlotDeclaration) -> ImageDeclaration:
    try:
        return declared(slot, declaration)
    except ValidationError as refused:
        raise InvalidInput("; ".join(str(problem["msg"]) for problem in refused.errors())) from None


def _require_open(row: UploadLink, now: datetime) -> None:
    state = link_state(used_at=row.usedAt, expires_at=row.expiresAt, now=now)
    if state == USED:
        raise LinkGone(USED_DETAIL)
    if state != OPEN:
        raise LinkGone(EXPIRED_DETAIL)


def _owner_live(row: UploadLink, user: User) -> bool:
    claims = {TOKEN_VERSION_CLAIM: row.userTokenVersion, "iat": row.createdAt.timestamp()}
    return token_matches_user(claims, user)


async def _own_link(session: AsyncSession, user: User, token: str, *, lock: bool) -> UploadLink:
    digest = stored_secret(token, LINK_PREFIX)
    if digest is None:
        raise UnknownLink(token)
    if lock:
        row = await _locked(session, UploadLink.linkHash == digest)
    else:
        row = await session.scalar(select(UploadLink).where(UploadLink.linkHash == digest))
    if row is None or row.userId != user.id:
        raise UnknownLink(token)
    return row


async def _locked(session: AsyncSession, condition: ColumnElement[bool]) -> UploadLink | None:
    return await session.scalar(select(UploadLink).where(condition).with_for_update())


async def _refuse_too_many(session: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    held = await session.scalar(
        select(func.count())
        .select_from(UploadLink)
        .where(UploadLink.userId == user_id, UploadLink.usedAt.is_(None), UploadLink.expiresAt > now)
    )
    if int(held or 0) >= OPEN_LINKS_MAX:
        raise InvalidInput(TOO_MANY)


async def _craft(session: AsyncSession, slug: str) -> Craft:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise InvalidInput(NO_CRAFT.format(slug=slug))
    return craft


async def _stage(session: AsyncSession, craft_id: uuid.UUID, stage_id: uuid.UUID | None) -> SlotStage | None:
    if stage_id is None:
        return None
    name = await session.scalar(
        select(ProcessStage.name)
        .join(Process, Process.id == ProcessStage.processId)
        .where(ProcessStage.id == stage_id, Process.craftId == craft_id)
    )
    if name is None:
        raise InvalidInput(NO_STAGE)
    return SlotStage(id=stage_id, name=name)


async def _facts(session: AsyncSession, claim_ids: list[uuid.UUID]) -> list[SlotFact]:
    shown = await _shown_facts(session, claim_ids)
    found = {fact.id for fact in shown}
    missing = [claim_id for claim_id in claim_ids if claim_id not in found]
    if missing:
        raise InvalidInput(NO_FACT.format(claim_id=missing[0]))
    return shown


async def _shown_facts(session: AsyncSession, claim_ids: list[uuid.UUID]) -> list[SlotFact]:
    shown, _ = await knowledge_view.claims_by_id(session, claim_ids, acls=OPEN_CHUNK_ACLS)
    return [SlotFact(id=claim_id, text=shown[claim_id].text) for claim_id in claim_ids if claim_id in shown]


def _digest(token: str, prefix: str) -> str:
    digest = stored_secret(token, prefix)
    if digest is None:
        raise ValueError(f"a new secret starts with {prefix}")
    return digest
