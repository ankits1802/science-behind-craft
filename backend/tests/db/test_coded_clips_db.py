import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.data.kind_fixture_files import KIND_FIXTURES_DIR
from app.models import MediaAsset, MediaJob, User
from app.research.component_proposals import ComponentProposalDraft
from app.research.component_specs import checked_spec
from app.services import clip_stills, component_proposals
from app.services.coded_clips import filmed_spec, shared_clip
from app.services.naming import clip_still_key

from .page_documents_seed import CRAFT_CLAIM, CRAFT_SLUG, seed
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

KIND = "coded_figure"
FIXTURE = json.loads((KIND_FIXTURES_DIR / "coded_figure.json").read_text(encoding="utf-8"))
SHOWN = uuid.UUID("5a1d3c7e-9b2f-4e6a-8c1d-2e3f4a5b6c7d")
ELSEWHERE = uuid.UUID("7c3e5a9b-1d2f-4a6e-8b0c-4d5e6f7a8b9c")
MADE = datetime(2026, 11, 20, 20, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
JPEG = b"\xff\xd8\xff\xe0still"
RESEARCHER = uuid.UUID("9e0c0000-0000-4000-8000-0000000000d1")
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


@pytest.fixture
async def seeded() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        opened.add(
            User(
                id=RESEARCHER,
                name="Clip researcher",
                email=f"clips-{uuid.uuid4().hex[:8]}@example.org",
                role="RESEARCHER",
            )
        )
        await opened.flush()
        yield opened


class StillBucket:
    def __init__(self, stored: dict[str, bytes]) -> None:
        self.stored = dict(stored)

    async def get(self, key: str) -> bytes | None:
        return self.stored.get(key)

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        self.stored[key] = body


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


def filmed(clip: uuid.UUID) -> dict[str, object]:
    code = FIXTURE["spec"]["code"].replace("<ul ", '<video data-film="dip" controls></video><ul ', 1)
    films = [{"key": "dip", "clip": str(clip)}, {"key": "loop", "src": "/monographs/kit/films/bidri-dip.mp4"}]
    code = code.replace("<ul ", '<video data-film="loop"></video><ul ', 1)
    return {**FIXTURE["spec"], "code": code, "films": films}


def figure(clip: uuid.UUID) -> object:
    return checked_spec(KIND, filmed(clip))


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
    assert placed.clips == (found,)


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
    assert placed.spec is None and placed.clips == ()
    assert placed.problems == [
        f"the film dip names the clip {clip}, which is not a clip this page holds: name an approved video "
        "of the media store made from a fact the figure cites"
    ]


async def test_a_clip_nobody_stored_is_refused(session: AsyncSession) -> None:
    missing = uuid.uuid4()
    placed = await filmed_spec(session, figure(missing), [SHOWN])
    assert placed.spec is None and len(placed.problems) == 1 and str(missing) in placed.problems[0]


def delivered(spec: object, *, cited: uuid.UUID) -> ComponentProposalDraft:
    units = {
        ref: {"text": unit["text"], **({"claimIds": [str(cited)]} if unit.get("claims") else {})}
        for ref, unit in FIXTURE["units"].items()
    }
    return ComponentProposalDraft.model_validate(
        {
            "label": "page-docs-test-craft/chemistry/patina-bath-film",
            "title": "The patina bath, filmed",
            "description": "The bath that blackens the alloy, with the clip of the alloy darkening in it.",
            "kind": KIND,
            "field": "CHEMISTRY",
            "craft_slug": CRAFT_SLUG,
            "subjects": [{"kind": "CRAFT", "key": CRAFT_SLUG}],
            "spec": spec,
            "units": units,
        }
    )


def said_by(cited: uuid.UUID) -> dict[uuid.UUID, list[str]]:
    return {cited: [" ".join(str(unit["text"]) for unit in FIXTURE["units"].values())]}


async def test_a_delivered_figure_s_clip_has_its_still_cut_at_delivery(
    seeded: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    clip = await stored_clip(seeded, claims=[CRAFT_CLAIM])
    found = await shared_clip(seeded, clip)
    assert found is not None
    bucket = StillBucket({found.page_key: b"mp4 bytes"})
    cuts: list[float] = []

    async def cut(data: bytes, at_seconds: float) -> bytes:
        cuts.append(at_seconds)
        return JPEG

    monkeypatch.setattr(component_proposals, "media_bucket", lambda: bucket)
    monkeypatch.setattr(clip_stills, "ffmpeg_still", cut)
    researcher = await seeded.get(User, RESEARCHER)
    assert researcher is not None
    spec = filmed(clip)
    stored = await component_proposals.propose_component(
        seeded, researcher, delivered(spec, cited=CRAFT_CLAIM), now=NOW, known=said_by(CRAFT_CLAIM)
    )
    assert stored.outcome == "STORED"
    assert bucket.stored[clip_still_key(found.page_key)] == JPEG and cuts == [4.0]


async def test_a_delivered_figure_without_a_clip_cuts_no_still(
    seeded: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    bucket = StillBucket({})
    monkeypatch.setattr(component_proposals, "media_bucket", lambda: bucket)

    async def never(data: bytes, at_seconds: float) -> bytes:
        raise AssertionError("no clip to cut")

    monkeypatch.setattr(clip_stills, "ffmpeg_still", never)
    researcher = await seeded.get(User, RESEARCHER)
    assert researcher is not None
    plain = FIXTURE["spec"]
    stored = await component_proposals.propose_component(
        seeded, researcher, delivered(plain, cited=CRAFT_CLAIM), now=NOW, known=said_by(CRAFT_CLAIM)
    )
    assert stored.outcome == "STORED" and bucket.stored == {}
