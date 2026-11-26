from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from functools import cache

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import release_connection
from app.data.skill_library import (
    CRITIQUE_REFERENCE,
    DESIGN_SKILL,
    SKILL_ENTRY,
    SKILL_URI_PREFIX,
    reference_text,
    skill_file_text,
)
from app.models import DesignReadCache, User
from app.providers.design_vision import read_design
from app.providers.router import Principal
from app.research.design_read import (
    READ,
    SKIPPED,
    DesignRead,
    ModelReading,
    NotRead,
    design_read_of,
    drawing_skip,
    pictures_key,
    skipped,
)
from app.research.design_read_prompt import (
    DESIGN_FIRST_SECTION,
    DESIGN_LAST_SECTION_BEFORE,
    DesignGuidance,
    DesignRequest,
    ajrakh_rhythm,
    design_request,
    skill_sections,
)
from app.research.page_report import PageReport

from .page_report import bar_content
from .page_reviews import DrawnPreview

__all__ = [
    "CACHE_DAYS",
    "DesignReader",
    "cached_read",
    "design_guidance",
    "designed_preview",
    "store_read",
]

CACHE_DAYS = 30
DESIGN_SKILL_URI = f"{SKILL_URI_PREFIX}{DESIGN_SKILL}/{SKILL_ENTRY}"

DesignReader = Callable[[DesignRequest, Principal], Awaitable[ModelReading | NotRead]]


async def designed_preview(
    session: AsyncSession,
    user: User,
    drawn: DrawnPreview,
    *,
    asked: bool,
    now: datetime,
    reader: DesignReader = read_design,
) -> DrawnPreview:
    if not asked or drawn.report is None:
        return drawn
    read = await _read(session, user, drawn, now=now, reader=reader)
    return DrawnPreview(report=_with_read(drawn.report, read), images=drawn.images)


async def cached_read(session: AsyncSession, key: str) -> DesignRead | None:
    row = await session.get(DesignReadCache, key)
    if row is None:
        return None
    try:
        held = DesignRead.model_validate(row.reading)
    except ValidationError:
        return None
    return held.model_copy(update={"cached": True, "cost_usd": Decimal(0)})


async def store_read(session: AsyncSession, key: str, read: DesignRead, *, now: datetime) -> None:
    await session.execute(
        delete(DesignReadCache).where(DesignReadCache.createdAt < now - timedelta(days=CACHE_DAYS))
    )
    await session.execute(
        insert(DesignReadCache)
        .values(
            picturesKey=key,
            reading=read.model_dump(mode="json"),
            provider=read.provider or "",
            model=read.model or "",
            costUsd=read.cost_usd,
            createdAt=now,
        )
        .on_conflict_do_nothing(index_elements=["picturesKey"])
    )


@cache
def design_guidance() -> DesignGuidance:
    return DesignGuidance(
        rubric=reference_text(CRITIQUE_REFERENCE),
        sections=skill_sections(
            skill_file_text(DESIGN_SKILL_URI), DESIGN_FIRST_SECTION, DESIGN_LAST_SECTION_BEFORE
        ),
        rhythm=ajrakh_rhythm(bar_content()),
    )


async def _read(
    session: AsyncSession, user: User, drawn: DrawnPreview, *, now: datetime, reader: DesignReader
) -> DesignRead:
    reason = drawing_skip(drawn.report.drawing if drawn.report else None, drawn.images)
    if reason is not None:
        return skipped(reason)
    key = pictures_key(drawn.images)
    held = await cached_read(session, key)
    if held is not None:
        return held
    request = design_request(drawn.images, design_guidance())
    await release_connection(session)
    reading = await reader(request, Principal(user_id=user.id, role=user.role))
    if isinstance(reading, NotRead):
        return DesignRead(state=SKIPPED, reason=reading.reason, chapters=list(request.chapters))
    read = design_read_of(reading, request.chapters)
    if read.state == READ:
        await store_read(session, key, read, now=now)
    return read


def _with_read(report: PageReport, read: DesignRead) -> PageReport:
    return report.model_copy(update={"design_read": read})
