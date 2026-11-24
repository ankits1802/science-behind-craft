import uuid
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Chunk,
    Claim,
    ClaimSource,
    Concept,
    ConditionReading,
    EnvDataset,
    ImageContribution,
    MapLayerProposal,
    MediaAsset,
    Process,
    ProcessCondition,
    ProcessStage,
    Source,
    StageReview,
)
from app.research.page_layout import PageLayoutEntry
from app.research.staged_reviews import StagedDecision
from app.services.claim_writer import LIVE_CONCEPT_ORIGIN
from app.services.open_work_subjects import craft_subject
from app.services.page_layouts import store_layout

from .review_queue_seed import CONCEPT, CRAFT, LIVE, NOW, SLUG, SOURCE, People, seeded_session

__all__ = [
    "ASSET",
    "CHUNK",
    "HELD_READING",
    "LATER_STAGE",
    "LAYER",
    "PICTURE",
    "PLACED",
    "PLACED_STAGE",
    "QUOTE",
    "QUOTED",
    "READING",
    "SECOND_SOURCE",
    "STAGE",
    "THIRD_SOURCE",
    "WHY",
    "decided",
    "published_session",
]

WHY = "It shows another craft's work on this page."
QUOTE = "Lime keeps the indigo vat alkaline, so the dye stays reduced"
PASSAGE = f"In the courtyard dye house, {QUOTE}, and the dyers stir it twice a day."


def key(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-published-content/{name}")


PICTURE, ASSET, QUOTED, CITED, CHUNK = key("picture"), key("asset"), key("quoted"), key("cited"), key("chunk")
SECOND_SOURCE, THIRD_SOURCE, THIRD_CITE = key("second"), key("third"), key("third-cite")
PROCESS, STAGE, PLACED_STAGE, LATER_STAGE = key("process"), key("stage"), key("placed-stage"), key("later")
PLACED, CONDITION, READING, HELD_READING = (
    key("placed"),
    key("condition"),
    key("reading"),
    key("held-reading"),
)
DATASET, LAYER = key("dataset"), key("layer")


def decided(kind: str, item: uuid.UUID, action: str, **more: Any) -> StagedDecision:
    return StagedDecision.model_validate({"kind": kind, "id": item, "action": action, "reason": WHY, **more})


async def published_session() -> AsyncIterator[tuple[AsyncSession, People]]:
    async for opened, people in seeded_session():
        await _sources(opened)
        await _quoted(opened)
        await _process(opened, people)
        await _picture(opened, people)
        await _layer(opened, people)
        await _layouts(opened, people)
        yield opened, people


async def _sources(session: AsyncSession) -> None:
    session.add_all(
        [
            Source(id=SECOND_SOURCE, kind="WEB_PAGE", title="A dye house visit", licence="CC-BY-4.0"),
            Source(id=THIRD_SOURCE, kind="WEB_PAGE", title="Vat notes", licence="CC-BY-4.0"),
            Chunk(id=CHUNK, sourceId=SOURCE, ordinal=0, locator="p. 4", text=PASSAGE),
        ]
    )
    await session.flush()
    session.add_all(
        [
            ClaimSource(claimId=LIVE, sourceId=SECOND_SOURCE, quote="lime in the vat", locator="visit"),
            ClaimSource(
                id=THIRD_CITE, claimId=LIVE, sourceId=THIRD_SOURCE, quote="the vat at 30", locator="n. 2"
            ),
        ]
    )
    await session.flush()


async def _quoted(session: AsyncSession) -> None:
    session.add(
        Claim(
            id=QUOTED,
            subjectType="CONCEPT",
            subjectId=CONCEPT,
            predicate="states",
            text="Lime keeps the indigo vat alkaline.",
            evidenceLevel="PROVISIONAL",
            origin="IMPORT",
            status="APPROVED",
            field="CHEMISTRY",
        )
    )
    await session.flush()
    session.add(
        ClaimSource(
            id=CITED,
            claimId=QUOTED,
            sourceId=SOURCE,
            chunkId=CHUNK,
            quote=QUOTE,
            locator="p. 4",
            quoteCheck="PASS",
        )
    )
    await session.flush()


async def _process(session: AsyncSession, people: People) -> None:
    session.add(Process(id=PROCESS, craftId=CRAFT, name="Dyeing"))
    session.add(
        Concept(id=PLACED, craftId=CRAFT, type="PROCESS_STAGE", name="Airing", originRef=LIVE_CONCEPT_ORIGIN)
    )
    await session.flush()
    session.add_all(
        [
            ProcessStage(id=STAGE, processId=PROCESS, ordinal=1, name="Reducing the vat", stageType="DYE"),
            ProcessStage(id=PLACED_STAGE, processId=PROCESS, ordinal=2, name="Airing", conceptId=PLACED),
            ProcessStage(id=LATER_STAGE, processId=PROCESS, ordinal=3, name="Washing"),
        ]
    )
    await session.flush()
    session.add(
        StageReview(
            conceptId=PLACED, status="PLACED", reviewerId=people.admin.id, processStageId=PLACED_STAGE
        )
    )
    session.add(
        ProcessCondition(
            id=CONDITION, stageId=STAGE, key="vat-heat", label="Vat heat", quantity="TEMPERATURE"
        )
    )
    await session.flush()
    session.add_all([_reading(READING, CITED), _reading(HELD_READING, THIRD_CITE)])
    await session.flush()


def _reading(reading_id: uuid.UUID, cited: uuid.UUID) -> ConditionReading:
    return ConditionReading(
        id=reading_id,
        conditionId=CONDITION,
        claimSourceId=cited,
        stated="30 °C",
        statedMin=Decimal(30),
        statedMax=Decimal(30),
        statedUnit="°C",
    )


async def _picture(session: AsyncSession, people: People) -> None:
    session.add(
        MediaAsset(
            id=ASSET,
            s3Key=f"media/published/{ASSET.hex}.png",
            mime="image/png",
            width=800,
            height=600,
            visibility="CRAFT_SHARED",
        )
    )
    await session.flush()
    session.add(
        ImageContribution(
            id=PICTURE,
            contributorId=people.researcher.id,
            craftId=CRAFT,
            claimIds=[],
            origin="PHOTOGRAPH",
            caption="The vat turns yellow-green",
            altText="A clay vat of yellow-green liquid",
            termsVersion="2026-11-19",
            rightsConfirmedAt=NOW,
            status="APPROVED",
            assetId=ASSET,
            sha256="a" * 64,
            reviewedById=people.admin.id,
            reviewedAt=NOW,
        )
    )
    await session.flush()


async def _layer(session: AsyncSession, people: People) -> None:
    session.add(EnvDataset(id=DATASET, code="TEST-PUBLISHED-SITES", title="Test mineral sites"))
    await session.flush()
    session.add(
        MapLayerProposal(
            id=LAYER,
            datasetId=DATASET,
            proposerId=people.researcher.id,
            plan={},
            layer={},
            featureCount=3,
            byteSize=1200,
            sha256="b" * 64,
            status="APPROVED",
            reviewedById=people.admin.id,
            reviewedAt=NOW,
        )
    )
    await session.flush()


async def _layouts(session: AsyncSession, people: People) -> None:
    page = await craft_subject(session, SLUG)
    first = [PageLayoutEntry(ref="u0001", chapter="glance", order=1, role="BODY")]
    await store_layout(session, page, first, actor=None)
    second = [*first, PageLayoutEntry(ref="u0002", chapter="glance", order=2, role="BODY")]
    await store_layout(session, page, second, actor=people.admin)
