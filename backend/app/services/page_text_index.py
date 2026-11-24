from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import batched
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PageTextUnit, PageTranslation
from app.research.monograph_page import MonographContent
from app.research.page_passages import PagePassage, page_passages
from app.research.page_translations import LIVE_TRANSLATION_STATUSES
from app.research.translation_passages import PassageLeaf, TaskPassage, passage_text

__all__ = [
    "INDEX_EDITION",
    "PageKey",
    "Specs",
    "covered_counts",
    "indexed_passages",
    "indexed_tag",
    "refresh_page_texts",
    "stored_tag",
    "text_counts",
    "write_page_texts",
]

CHAPTER_MAX = 80
INDEX_EDITION = "i2"
EDITION_SEPARATOR = "-"
TAG_MAX = 16
ROWS_PER_INSERT = 500
PRIMARY_KEY = ("subjectKind", "subjectSlug", "unitKey")
REFRESHED = ("position", "sourceHash", "chapter", "tag", "leaves", "documentTag", "refreshedAt")

PageKey = tuple[str, str]
Specs = Mapping[str, Mapping[str, Any]]


def stored_tag(version: int, content_hash: str) -> str:
    return f"v{version}-{content_hash}"


async def indexed_tag(session: AsyncSession, page: PageKey) -> str | None:
    kind, slug = page
    filed = await session.scalar(
        select(PageTextUnit.documentTag)
        .where(PageTextUnit.subjectKind == kind, PageTextUnit.subjectSlug == slug)
        .limit(1)
    )
    edition = f"{EDITION_SEPARATOR}{INDEX_EDITION}"
    return filed.removesuffix(edition) if filed is not None and filed.endswith(edition) else None


async def refresh_page_texts(
    session: AsyncSession,
    page: PageKey,
    tag: str,
    content: MonographContent,
    specs: Specs,
    *,
    now: datetime | None = None,
) -> bool:
    if await indexed_tag(session, page) == tag:
        return False
    await write_page_texts(session, page, tag, content, specs, now=now)
    return True


async def write_page_texts(
    session: AsyncSession,
    page: PageKey,
    tag: str,
    content: MonographContent,
    specs: Specs,
    *,
    now: datetime | None = None,
) -> None:
    kind, slug = page
    rows = _index_rows(page, tag, page_passages(content, specs).values(), now or datetime.now(UTC))
    await session.execute(
        delete(PageTextUnit).where(PageTextUnit.subjectKind == kind, PageTextUnit.subjectSlug == slug)
    )
    for chunk in batched(rows, ROWS_PER_INSERT, strict=False):
        added = insert(PageTextUnit).values(list(chunk))
        kept = {name: added.excluded[name] for name in REFRESHED}
        await session.execute(added.on_conflict_do_update(index_elements=PRIMARY_KEY, set_=kept))
    await session.flush()


def _index_rows(
    page: PageKey, tag: str, passages: Iterable[PagePassage], now: datetime
) -> list[dict[str, Any]]:
    kind, slug = page
    return [
        {
            "subjectKind": kind,
            "subjectSlug": slug,
            "unitKey": passage.key,
            "position": position,
            "sourceHash": passage.source_hash,
            "chapter": passage.chapter[:CHAPTER_MAX],
            "tag": passage.tag[:TAG_MAX],
            "leaves": [asdict(leaf) for leaf in passage.leaves()],
            "documentTag": f"{tag}{EDITION_SEPARATOR}{INDEX_EDITION}",
            "refreshedAt": now,
        }
        for position, passage in enumerate(passages)
    ]


async def indexed_passages(session: AsyncSession, page: PageKey) -> list[TaskPassage]:
    kind, slug = page
    rows = await session.scalars(
        select(PageTextUnit)
        .where(PageTextUnit.subjectKind == kind, PageTextUnit.subjectSlug == slug)
        .order_by(PageTextUnit.position)
    )
    return [_passage(row) for row in rows.all()]


def _passage(row: PageTextUnit) -> TaskPassage:
    leaves = [PassageLeaf(**leaf) for leaf in row.leaves]
    return TaskPassage(
        key=row.unitKey,
        source_hash=row.sourceHash,
        english=passage_text(leaves),
        texts=[leaf.text for leaf in leaves],
        fixed=[at for at, leaf in enumerate(leaves) if leaf.fixed],
        cited=[at for at, leaf in enumerate(leaves) if leaf.cited],
    )


async def text_counts(session: AsyncSession, slugs: Sequence[str]) -> dict[PageKey, int]:
    rows = await session.execute(
        select(PageTextUnit.subjectKind, PageTextUnit.subjectSlug, func.count())
        .where(PageTextUnit.subjectSlug.in_(slugs))
        .group_by(PageTextUnit.subjectKind, PageTextUnit.subjectSlug)
    )
    return {(str(kind), str(slug)): int(count) for kind, slug, count in rows.all()}


async def covered_counts(
    session: AsyncSession, slugs: Sequence[str], statuses: Sequence[str] = LIVE_TRANSLATION_STATUSES
) -> dict[tuple[str, str, str], int]:
    rows = await session.execute(
        select(
            PageTextUnit.subjectKind,
            PageTextUnit.subjectSlug,
            PageTranslation.language,
            func.count(func.distinct(PageTextUnit.unitKey)),
        )
        .join(
            PageTranslation,
            (PageTranslation.subjectKind == PageTextUnit.subjectKind)
            & (PageTranslation.subjectSlug == PageTextUnit.subjectSlug)
            & (PageTranslation.sourceHash == PageTextUnit.sourceHash),
        )
        .where(PageTextUnit.subjectSlug.in_(slugs), PageTranslation.status.in_(statuses))
        .group_by(PageTextUnit.subjectKind, PageTextUnit.subjectSlug, PageTranslation.language)
    )
    return {(str(kind), str(slug), str(language)): int(count) for kind, slug, language, count in rows.all()}
