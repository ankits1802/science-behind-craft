import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import (
    ArticleSection,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    KnowledgePiece,
    KnowledgePieceSubject,
    Source,
    User,
    WebFetch,
)

__all__ = [
    "CHEMISTRY_FACT",
    "CRAFT",
    "DEAD",
    "HISTORY_ONE_SOURCE",
    "NOW",
    "OTHER",
    "PROFESSOR",
    "RESEARCHER",
    "SITE",
    "SLUG",
    "UNARCHIVED",
    "WHAT_IF",
    "opened_session",
]

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
SITE = "https://kalavigyan.example"
SLUG = "Open-Work-Test-Craft"
CRAFT = uuid.UUID("0a000000-0000-4000-8000-000000000001")
ALUM = uuid.UUID("0a000000-0000-4000-8000-000000000002")
HISTORY_ONE_SOURCE = uuid.UUID("0a000000-0000-4000-8000-000000000011")
HISTORY_TWO_SOURCES = uuid.UUID("0a000000-0000-4000-8000-000000000012")
CHEMISTRY_FACT = uuid.UUID("0a000000-0000-4000-8000-000000000013")
UNARCHIVED = uuid.UUID("0a000000-0000-4000-8000-000000000021")
ARCHIVED = uuid.UUID("0a000000-0000-4000-8000-000000000022")
DEAD = uuid.UUID("0a000000-0000-4000-8000-000000000023")
RESEARCHER = uuid.UUID("0a000000-0000-4000-8000-000000000031")
OTHER = uuid.UUID("0a000000-0000-4000-8000-000000000032")
PROFESSOR = uuid.UUID("0a000000-0000-4000-8000-000000000033")
WHAT_IF = "open-work-test-craft/history/what-if-the-zircovane-mordant-were-skipped"
TEST_HOST = "https://open-work-test.example"


async def opened_session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            await _seed(session)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def _seed(session: AsyncSession) -> None:
    session.add(Craft(id=CRAFT, name="Open Work Test Craft", slug=SLUG, giStatus="GI"))
    for user_id, role in ((RESEARCHER, "RESEARCHER"), (OTHER, "RESEARCHER"), (PROFESSOR, "PROFESSOR")):
        session.add(
            User(
                id=user_id,
                name=f"{role.title()} {user_id.hex[-4:]}",
                email=f"{user_id.hex}@example.org",
                role=role,
            )
        )
    session.add(Concept(id=ALUM, craftId=CRAFT, type="MATERIAL", name="Zircovane"))
    session.add(Source(id=UNARCHIVED, kind="WEB_PAGE", title="A live page", url=f"{TEST_HOST}/live"))
    session.add(
        Source(
            id=ARCHIVED,
            kind="WEB_PAGE",
            title="An archived page",
            url=f"{TEST_HOST}/kept",
            externalIds={"archivedUrl": f"https://web.archive.org/web/2026/{TEST_HOST}/kept"},
        )
    )
    session.add(Source(id=DEAD, kind="WEB_PAGE", title="A page now gone", url=f"{TEST_HOST}/gone"))
    session.add(WebFetch(url=f"{TEST_HOST}/gone", status=404, fetchedAt=NOW))
    await session.flush()
    await _facts(session)
    await _section_and_component(session)


async def _facts(session: AsyncSession) -> None:
    session.add(_claim(HISTORY_ONE_SOURCE, "The zircovane print came to the town in 1890.", field="HISTORY"))
    session.add(_claim(HISTORY_TWO_SOURCES, "Printers moved the zircovane blocks east.", field="HISTORY"))
    session.add(
        _claim(
            CHEMISTRY_FACT,
            "Zircovane binds the dye to cotton.",
            field="CHEMISTRY",
            fields=["HISTORY"],
            sourcesDiffer=True,
        )
    )
    await session.flush()
    for claim_id, source_id in (
        (HISTORY_ONE_SOURCE, UNARCHIVED),
        (HISTORY_TWO_SOURCES, UNARCHIVED),
        (HISTORY_TWO_SOURCES, ARCHIVED),
        (CHEMISTRY_FACT, DEAD),
    ):
        session.add(
            ClaimSource(
                claimId=claim_id, sourceId=source_id, quote="a quoted passage of the source", locator="p. 1"
            )
        )
    await session.flush()


async def _section_and_component(session: AsyncSession) -> None:
    sentences = [{"text": "The print came in 1890.", "claimIds": [str(HISTORY_ONE_SOURCE)]}] * 2
    session.add(
        ArticleSection(craftId=CRAFT, field="HISTORY", version=1, status="PUBLISHED", sentences=sentences)
    )
    piece = KnowledgePiece(
        id=uuid.uuid4(),
        craftId=CRAFT,
        kind="what_if",
        facet="HISTORY",
        topicKey=f"component:{WHAT_IF}",
        language="en",
        depth="EXPERT",
        payload={},
        claimIds=[HISTORY_ONE_SOURCE],
        sourceIds=[str(UNARCHIVED)],
        contentHash="3" * 64,
        label=WHAT_IF,
        title="What if the zircovane mordant were skipped",
        description="A toggle that shows the cloth printed with and without the zircovane mordant bath.",
    )
    session.add(piece)
    await session.flush()
    session.add(KnowledgePieceSubject(pieceId=piece.id, kind="CRAFT", craftId=CRAFT))
    await session.flush()


def _claim(claim_id: uuid.UUID, text: str, **changes: Any) -> Claim:
    return Claim(
        id=claim_id,
        subjectType="CONCEPT",
        subjectId=ALUM,
        predicate="states",
        text=text,
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        **changes,
    )
