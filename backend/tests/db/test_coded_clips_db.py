import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.data.kind_fixture_files import KIND_FIXTURES_DIR
from app.models import MediaAsset, MediaJob
from app.research.component_specs import checked_spec
from app.services.coded_clips import filmed_spec, shared_clip

pytestmark = pytest.mark.db

KIND = "coded_figure"
FIXTURE = json.loads((KIND_FIXTURES_DIR / "coded_figure.json").read_text(encoding="utf-8"))
SHOWN = uuid.UUID("5a1d3c7e-9b2f-4e6a-8c1d-2e3f4a5b6c7d")
ELSEWHERE = uuid.UUID("7c3e5a9b-1d2f-4a6e-8b0c-4d5e6f7a8b9c")
MADE = datetime(2026, 11, 20, 20, 0, tzinfo=UTC)
LEAF = "KalaVigyan_Generated-Video_2026-11-21_0130_Bidar_Bidriware_Patina-Bath_Video_Step-04.mp4"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with factory() as opened:
                yield opened
        finally:
            await transaction.rollback()


async def stored_clip(session: AsyncSession, **changes: object) -> uuid.UUID:
    made = {
        "kind": "VIDEO",
        "status": "SUCCEEDED",
        "visibility": "CRAFT_SHARED",
        "claims": [SHOWN],
        **changes,
    }
    job = MediaJob(
        id=uuid.uuid4(),
        kind=made["kind"],
        status=made["status"],
        claimIds=made["claims"],
        model="veo-3.1-fast",
        idempotencyKey=f"media:{uuid.uuid4().hex}",
        costUsd=Decimal("0"),
    )
    session.add(job)
    await session.flush()
    digest = uuid.uuid4().hex * 2
    asset = MediaAsset(
        id=uuid.uuid4(),
        jobId=job.id,
        s3Key=f"media/{uuid.uuid4()}/{uuid.uuid4().hex}/{LEAF}",
        pageKey=f"media/craft/{digest}/{LEAF}",
        mime="video/mp4",
        durationS=Decimal("8.000"),
        model="veo-3.1-fast",
        altText="The alloy darkens in the bath.",
        visibility=made["visibility"],
        createdAt=MADE,
    )
    session.add(asset)
    await session.flush()
    return asset.id


def figure(clip: uuid.UUID) -> object:
    code = FIXTURE["spec"]["code"].replace("<ul ", '<video data-film="dip" controls></video><ul ', 1)
    films = [{"key": "dip", "clip": str(clip)}, {"key": "loop", "src": "/monographs/kit/films/bidri-dip.mp4"}]
    code = code.replace("<ul ", '<video data-film="loop"></video><ul ', 1)
    return checked_spec(KIND, {**FIXTURE["spec"], "code": code, "films": films})


async def test_a_shared_video_made_from_a_cited_fact_is_kept_with_its_credit(session: AsyncSession) -> None:
    clip = await stored_clip(session)
    placed = await filmed_spec(session, figure(clip), [SHOWN])
    assert placed.problems == [] and placed.spec is not None
    assert placed.spec["films"] == [
        {"key": "dip", "clip": str(clip), "credit": "AI video, made with veo-3.1-fast on 2026-11-21"},
        {"key": "loop", "src": "/monographs/kit/films/bidri-dip.mp4"},
    ]
    found = await shared_clip(session, clip)
    assert found is not None and found.page_key.endswith(LEAF) and found.duration_seconds == 8.0


@pytest.mark.parametrize(
    "changes",
    [
        {"visibility": "PRIVATE"},
        {"kind": "IMAGE"},
        {"status": "FAILED"},
        {"claims": [ELSEWHERE]},
    ],
    ids=["private", "an image", "not succeeded", "of another craft's facts"],
)
async def test_a_clip_the_page_does_not_hold_is_refused_by_its_key(
    session: AsyncSession, changes: dict[str, object]
) -> None:
    clip = await stored_clip(session, **changes)
    placed = await filmed_spec(session, figure(clip), [SHOWN])
    assert placed.spec is None
    assert placed.problems == [
        f"the film dip names the clip {clip}, which is not a clip this page holds: name an approved video "
        "of the media store made from a fact the figure cites"
    ]


async def test_a_clip_nobody_stored_is_refused(session: AsyncSession) -> None:
    missing = uuid.uuid4()
    placed = await filmed_spec(session, figure(missing), [SHOWN])
    assert placed.spec is None and len(placed.problems) == 1 and str(missing) in placed.problems[0]
