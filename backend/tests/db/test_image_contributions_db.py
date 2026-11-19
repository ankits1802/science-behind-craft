import uuid
import zlib
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Claim, ClaimSource, Concept, Craft, ImageContribution, MediaAsset, Source, User
from app.research.image_contributions import IMAGE_TERMS_VERSION, ImageDeclaration
from app.services import image_contributions as images
from app.services.object_store import PresignedGet

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)
SLUG = "Image-Contribution-Test-Craft"
CRAFT = uuid.UUID("1a6e0000-0000-4000-8000-000000000001")
CONCEPT = uuid.UUID("1a6e0000-0000-4000-8000-000000000002")
SOURCE = uuid.UUID("1a6e0000-0000-4000-8000-000000000003")
FACT = uuid.UUID("1a6e0000-0000-4000-8000-000000000004")
AI_SOURCE = b"http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class Objects:
    puts: dict[str, tuple[bytes, str]] = field(default_factory=dict)

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        self.puts[key] = (body, content_type)

    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet:
        return PresignedGet(url=f"https://bucket.test/{key}", expires_at=now + timedelta(seconds=seconds))


@dataclass(frozen=True)
class People:
    researcher: User
    other_researcher: User
    professor: User
    admin: User


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        opened.add(Craft(id=CRAFT, name="Image Contribution Test Craft", slug=SLUG))
        opened.add(Source(id=SOURCE, kind="PAPER", title="Indigo vats", licence="CC-BY-4.0", year=2020))
        await opened.flush()
        opened.add(Concept(id=CONCEPT, craftId=CRAFT, type="MATERIAL", name="Indigo"))
        await opened.flush()
        opened.add(_fact())
        await opened.flush()
        opened.add(
            ClaimSource(
                claimId=FACT,
                sourceId=SOURCE,
                quote="the reduced vat is yellow-green",
                locator="p. 4",
                quoteCheck="PASS",
                relation="DIRECT",
            )
        )
        await opened.flush()
        yield opened


@pytest.fixture
async def people(session: AsyncSession) -> People:
    made = People(*(_person(role) for role in ("RESEARCHER", "RESEARCHER", "PROFESSOR", "ADMIN")))
    session.add_all([made.researcher, made.other_researcher, made.professor, made.admin])
    await session.flush()
    return made


def _fact() -> Claim:
    return Claim(
        id=FACT,
        subjectType="CONCEPT",
        subjectId=CONCEPT,
        predicate="states",
        text="A reduced indigo vat is yellow-green.",
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        field="CHEMISTRY",
    )


def _person(role: str) -> User:
    key = uuid.uuid4()
    return User(id=key, name=f"{role.title()} {key.hex[:4]}", email=f"{key.hex[:12]}@example.org", role=role)


def _declaration(**changes: Any) -> ImageDeclaration:
    values: dict[str, Any] = {
        "craftSlug": SLUG,
        "claimIds": [str(FACT)],
        "origin": "AI_GENERATED",
        "generator": "ChatGPT, gpt-image-1",
        "prompt": "An indigo vat turning yellow-green as it is reduced",
        "caption": "The vat turns yellow-green as indigo is reduced",
        "altText": "A clay vat of yellow-green liquid with a blue film",
        "rightsConfirmed": True,
        "termsVersion": IMAGE_TERMS_VERSION,
    }
    return ImageDeclaration.model_validate(values | changes)


def _png(width: int = 800, height: int = 600, *, note: bytes = b"") -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return len(payload).to_bytes(4) + kind + payload + zlib.crc32(kind + payload).to_bytes(4)

    header = width.to_bytes(4) + height.to_bytes(4) + bytes([8, 2, 0, 0, 0])
    text = chunk(b"iTXt", note) if note else b""
    return PNG_SIGNATURE + chunk(b"IHDR", header) + text + chunk(b"IDAT", b"\x78\x9c") + chunk(b"IEND", b"")


async def _sent(session: AsyncSession, user: User, data: bytes, **changes: Any) -> ImageContribution:
    row = await images.declare(session, user, _declaration(**changes), now=NOW)
    upload = images.Upload(contribution_id=row.id, user=user, data=data)
    return await images.receive_file(session, upload, objects=cast(Any, Objects()), now=NOW)


async def test_a_researchers_ai_picture_waits_private_and_an_admin_shares_it(
    session: AsyncSession, people: People
) -> None:
    row = await _sent(session, people.researcher, _png(note=AI_SOURCE))
    asset = await session.get(MediaAsset, row.assetId)
    assert (row.status, row.aiMarked, asset is not None and asset.visibility) == ("PENDING", True, "PRIVATE")
    assert asset is not None and (asset.model, asset.width, asset.height) == (
        "ChatGPT, gpt-image-1",
        800,
        600,
    )
    await images.approve(session, row.id, people.admin, "Matches the fact", now=NOW)
    assert (row.status, row.reviewedById, asset.visibility, asset.approvedById) == (
        "APPROVED",
        people.admin.id,
        "CRAFT_SHARED",
        people.admin.id,
    )


async def test_a_professors_picture_is_approved_at_once(session: AsyncSession, people: People) -> None:
    row = await _sent(session, people.professor, _png())
    asset = await session.get(MediaAsset, row.assetId)
    assert (row.status, row.reviewedById, asset is not None and asset.visibility) == (
        "APPROVED",
        people.professor.id,
        "CRAFT_SHARED",
    )


async def test_a_photograph_whose_own_metadata_says_ai_made_is_refused(
    session: AsyncSession, people: People
) -> None:
    with pytest.raises(InvalidInput):
        await _sent(
            session, people.researcher, _png(note=AI_SOURCE), origin="PHOTOGRAPH", generator=None, prompt=None
        )


async def test_the_same_picture_twice_is_refused(session: AsyncSession, people: People) -> None:
    await _sent(session, people.researcher, _png())
    with pytest.raises(images.ContributionRefused):
        await _sent(session, people.other_researcher, _png())


async def test_a_picture_is_decided_once_and_never_by_its_contributor(
    session: AsyncSession, people: People
) -> None:
    row = await _sent(session, people.researcher, _png())
    with pytest.raises(images.ContributionRefused):
        await images.approve(session, row.id, people.researcher, None, now=NOW)
    await images.reject(session, row.id, people.admin, "The colour is wrong", now=NOW)
    with pytest.raises(images.ContributionRefused):
        await images.approve(session, row.id, people.admin, None, now=NOW)


async def test_only_the_contributor_sends_the_file_and_only_once(
    session: AsyncSession, people: People
) -> None:
    row = await images.declare(session, people.researcher, _declaration(), now=NOW)
    stranger = images.Upload(contribution_id=row.id, user=people.other_researcher, data=_png())
    with pytest.raises(images.UnknownImage):
        await images.receive_file(session, stranger, objects=cast(Any, Objects()), now=NOW)
    own = images.Upload(contribution_id=row.id, user=people.researcher, data=_png())
    await images.receive_file(session, own, objects=cast(Any, Objects()), now=NOW)
    with pytest.raises(images.ContributionRefused):
        await images.receive_file(session, own, objects=cast(Any, Objects()), now=NOW)


async def test_a_declaration_names_a_real_craft_stage_and_shown_facts(
    session: AsyncSession, people: People
) -> None:
    with pytest.raises(InvalidInput):
        await images.declare(session, people.researcher, _declaration(craftSlug="No-Such-Craft"), now=NOW)
    with pytest.raises(InvalidInput):
        await images.declare(session, people.researcher, _declaration(stageId=str(uuid.uuid4())), now=NOW)
    with pytest.raises(InvalidInput):
        await images.declare(session, people.researcher, _declaration(claimIds=[str(uuid.uuid4())]), now=NOW)


async def test_withdrawing_an_approved_picture_hides_it_again(session: AsyncSession, people: People) -> None:
    row = await _sent(session, people.professor, _png())
    await images.withdraw(session, row.id, people.professor)
    asset = await session.get(MediaAsset, row.assetId)
    assert (row.status, asset is not None and asset.visibility) == ("WITHDRAWN", "PRIVATE")
    assert [found.id for found in await images.queue(session, "WITHDRAWN") if found.id == row.id] == [row.id]


async def test_a_view_labels_an_ai_picture_as_an_illustration_with_its_tool(
    session: AsyncSession, people: People
) -> None:
    row = await _sent(session, people.researcher, _png())
    (view,) = await images.views(session, [row], objects=cast(Any, Objects()), now=NOW)
    assert view.label == "Illustration, made with ChatGPT, gpt-image-1"
    assert (
        view.craft_slug == SLUG
        and view.file_url is not None
        and view.file_url.startswith("https://bucket.test/")
    )
