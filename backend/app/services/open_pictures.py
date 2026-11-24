from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from urllib.parse import unquote, urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ExternalFailure, InvalidInput
from app.models import Craft, ImageContribution, OpenPicture, User
from app.research.craft_contributed import contributed_key
from app.research.image_contributions import OPEN_LICENCE, BatchPicture, shown_label
from app.research.image_contributions_give import GivenPicture
from app.research.image_intake_fetch import PictureFetcher
from app.research.image_intake_pixels import PREVIEW_MIME, thumbnail
from app.research.image_screens import ScreenTools
from app.research.open_pictures import (
    OPEN_TERMS_VERSION,
    SITE_NAMES,
    OpenLink,
    OpenPictureRecord,
    OpenSource,
    open_link,
    open_source,
)
from app.research.page_layout import picture_label
from app.research.upload_links import SlotCraft
from app.sources.images.open_picture_pages import open_picture_pages

from . import image_contributions as images
from .image_contributions_checks import check_claims, checked_craft, checked_target
from .image_contributions_errors import ContributionRefused
from .image_contributions_store import APPROVED
from .image_screens import Screened, same_picture, screened
from .live_sources import live_source_client
from .media_ref_store import stored_media_refs
from .object_store import ObjectStore
from .open_picture_rows import stored_open_picture
from .open_work_subjects import craft_subject
from .page_layouts_backfill import curated_pictures
from .upload_links_give import REPEATED, refusal_detail

__all__ = [
    "ON_THE_PAGE",
    "OpenGiven",
    "OpenPlacing",
    "OpenTools",
    "PicturePages",
    "PlacedPictures",
    "Thumbnail",
    "open_picture_reader",
    "page_key",
    "pages_on_the_page",
    "place_open_pictures",
]

LIVE_STATUSES = ("AWAITING_FILE", "PENDING", "APPROVED")
WWW = "www."
ON_THE_PAGE = "This picture is on the page already; choose another so no picture appears twice"
UNREAD = "{site} could not be read just now; try again in a few minutes"
UNFETCHED = "The picture's file could not be fetched just now; try again in a few minutes"


@dataclass(frozen=True)
class OpenGiven:
    position: int
    page_url: str
    picture: BatchPicture
    refused: str | None = None


@dataclass(frozen=True)
class OpenPlacing:
    craft_slug: str
    pictures: list[OpenGiven]


class PicturePages(Protocol):
    async def record(self, link: OpenLink) -> OpenPictureRecord: ...


@dataclass(frozen=True)
class OpenTools:
    pages: PicturePages
    fetcher: PictureFetcher
    screen: ScreenTools
    objects: ObjectStore
    now: datetime


@dataclass(frozen=True)
class Thumbnail:
    position: int
    credit: str
    data: bytes
    mime: str = PREVIEW_MIME


@dataclass(frozen=True)
class PlacedPictures:
    craft: SlotCraft
    pictures: list[GivenPicture]
    thumbnails: list[Thumbnail]
    given: int
    approved: int

    @property
    def refused(self) -> int:
        return len(self.pictures) - self.given


@dataclass(frozen=True)
class _Accepted:
    given: OpenGiven
    aimed: BatchPicture
    source: OpenSource
    screen: Screened


@dataclass
class _Placing:
    user: User
    craft: Craft
    tools: OpenTools
    taken: set[str]
    accepted: list[_Accepted] = field(default_factory=list)


@asynccontextmanager
async def open_picture_reader() -> AsyncIterator[PicturePages]:
    async with live_source_client() as client:
        yield open_picture_pages(client)


async def place_open_pictures(
    session: AsyncSession, user: User, placing: OpenPlacing, *, tools: OpenTools
) -> PlacedPictures:
    craft = await checked_craft(session, placing.craft_slug)
    batch = _Placing(user, craft, tools, await pages_on_the_page(session, craft))
    outcomes: dict[int, GivenPicture] = {}
    for given in placing.pictures:
        try:
            batch.accepted.append(await _screened(session, batch, given))
        except (InvalidInput, ContributionRefused) as refused:
            outcomes[given.position] = GivenPicture(position=given.position, refused=refusal_detail(refused))
    thumbnails: list[Thumbnail] = []
    for item in batch.accepted:
        row = await _filed(session, batch, item)
        outcomes[item.given.position] = _outcome(craft, item, row)
        shown = await _thumbnail(item)
        thumbnails += [shown] if shown is not None else []
    pictures = [outcomes[position] for position in sorted(outcomes)]
    approved = sum(picture.status == APPROVED for picture in pictures)
    shown_craft = SlotCraft(slug=craft.slug, name=craft.name)
    return PlacedPictures(shown_craft, pictures, thumbnails, given=len(batch.accepted), approved=approved)


async def pages_on_the_page(session: AsyncSession, craft: Craft) -> set[str]:
    live = await session.execute(
        select(OpenPicture.pageUrl, OpenPicture.fileUrl)
        .join(ImageContribution, ImageContribution.id == OpenPicture.contributionId)
        .where(ImageContribution.craftId == craft.id, ImageContribution.status.in_(LIVE_STATUSES))
    )
    curated = await curated_pictures(session, await craft_subject(session, craft.slug))
    media = await stored_media_refs(session, [picture.media_ref_id for picture in curated])
    shown = [address for row in live.all() for address in row]
    shown += [address for ref in media.values() for address in (ref.page_url, str(ref.image_url))]
    return {page_key(address) for address in shown}


def page_key(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower().removeprefix(WWW)
    path = unquote(parts.path).replace(" ", "_").rstrip("/")
    return f"{host}{path}?{parts.query}" if parts.query else f"{host}{path}"


async def _screened(session: AsyncSession, batch: _Placing, given: OpenGiven) -> _Accepted:
    if given.refused is not None:
        raise InvalidInput(given.refused)
    link = open_link(given.page_url)
    aimed = await checked_target(session, batch.craft, given.picture)
    await check_claims(session, aimed.claim_ids)
    record = await _record(batch.tools.pages, link)
    source = open_source(record)
    addresses = {page_key(source.page_url), page_key(source.file_url)}
    if addresses & batch.taken:
        raise ContributionRefused(ON_THE_PAGE)
    data = await _fetched(batch.tools.fetcher, record.fetch_url)
    screen = await screened(session, data, origin=OPEN_LICENCE, user=batch.user, tools=batch.tools.screen)
    if any(same_picture(screen, earlier.screen) for earlier in batch.accepted):
        raise ContributionRefused(REPEATED)
    batch.taken |= addresses
    return _Accepted(given, aimed, source, screen)


async def _record(pages: PicturePages, link: OpenLink) -> OpenPictureRecord:
    try:
        return await pages.record(link)
    except ExternalFailure:
        raise InvalidInput(UNREAD.format(site=SITE_NAMES[link.site])) from None


async def _fetched(fetcher: PictureFetcher, url: str) -> bytes:
    try:
        return (await fetcher.fetch_picture(url)).data
    except ExternalFailure:
        raise InvalidInput(UNFETCHED) from None


async def _filed(session: AsyncSession, batch: _Placing, item: _Accepted) -> ImageContribution:
    aimed, source = item.aimed, item.source
    row = ImageContribution(
        contributorId=batch.user.id,
        craftId=batch.craft.id,
        stageId=aimed.stage_id,
        materialId=aimed.material_id,
        slot=aimed.slot,
        taskKey=aimed.task_key,
        claimIds=list(aimed.claim_ids),
        origin=OPEN_LICENCE,
        caption=aimed.caption,
        altText=aimed.alt_text,
        termsVersion=OPEN_TERMS_VERSION,
        rightsConfirmedAt=source.read_at,
        status=images.AWAITING_FILE,
    )
    session.add(row)
    await session.flush()
    session.add(stored_open_picture(row.id, source))
    tools = batch.tools
    return await images.store_screened(
        session, row.id, batch.user, item.screen, objects=tools.objects, now=tools.now
    )


def _outcome(craft: Craft, item: _Accepted, row: ImageContribution) -> GivenPicture:
    image = item.screen.image
    return GivenPicture(
        position=item.given.position,
        contribution_id=row.id,
        status=row.status,
        label=shown_label(row.origin, None),
        received=image.received,
        mime=image.mime,
        width=image.width,
        height=image.height,
        screen=item.screen.summary(),
        open_source=item.source,
        plate=picture_label(craft.slug, contributed_key(row.id)),
    )


async def _thumbnail(item: _Accepted) -> Thumbnail | None:
    image = item.screen.image
    if image.vector:
        return None
    data = await asyncio.to_thread(thumbnail, image.data)
    return Thumbnail(position=item.given.position, credit=item.source.credit, data=data)
