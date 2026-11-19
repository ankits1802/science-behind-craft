import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, ImageContribution, MediaAsset, User
from app.research.image_contributions import IMAGE_TERMS_VERSION
from app.services import image_contributions as images, knowledge_view
from app.services.category_import import import_categories
from app.services.contributed_pictures import approved_pictures, shown_picture
from app.services.craft_page_snapshots import served_page
from app.services.craft_page_stamp import page_stamp
from app.services.curation_import import import_curation

from ..contracts.golden import golden_json
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

AJRAKH = "Kutch-Ajrakh"
NOW = datetime.now(UTC)
TOOL = "ChatGPT, gpt-image-1"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        yield opened


async def ajrakh(session: AsyncSession) -> Craft:
    assert (await import_curation(session)).refused == []
    assert (await import_categories(session)).refused == []
    craft = await knowledge_view.resolve_craft(session, AJRAKH)
    assert craft is not None
    return craft


def history_fact() -> uuid.UUID:
    claims = golden_json("craft.page.golden.json")["claims"]
    found = next(
        c
        for c in claims
        if c["discipline"] == "HISTORY" and c["level"] != "HYPOTHESIS" and c["provenance"] == "CURATED"
    )
    return uuid.UUID(found["id"])


async def person(session: AsyncSession, role: str) -> User:
    key = uuid.uuid4()
    user = User(id=key, name=f"{role.title()} {key.hex[:4]}", email=f"{key.hex[:12]}@example.org", role=role)
    session.add(user)
    await session.flush()
    return user


async def contributed(
    session: AsyncSession, craft: Craft, contributor: User, *, status: str, **changes: Any
) -> ImageContribution:
    key = uuid.uuid4().hex
    asset = MediaAsset(
        s3Key=f"media/{contributor.id}/{key}/KalaVigyan_Contribution_{key[:6]}.jpg",
        mime="image/jpeg",
        bytes=2048,
        width=1200,
        height=800,
        label="A printer at work",
        altText="A printer presses a carved block onto cloth",
        visibility="CRAFT_SHARED" if status == "APPROVED" else "PRIVATE",
    )
    session.add(asset)
    await session.flush()
    values: dict[str, Any] = {
        "contributorId": contributor.id,
        "craftId": craft.id,
        "origin": "PHOTOGRAPH",
        "caption": "A printer at work",
        "altText": "A printer presses a carved block onto cloth",
        "termsVersion": IMAGE_TERMS_VERSION,
        "rightsConfirmedAt": NOW,
        "status": status,
        "assetId": asset.id,
        "sha256": key + key[:32],
        "reviewedAt": NOW if status in ("APPROVED", "REJECTED") else None,
    }
    row = ImageContribution(**(values | changes))
    session.add(row)
    await session.flush()
    return row


async def test_only_the_craft_s_approved_shared_pictures_are_read_in_approval_order(
    session: AsyncSession,
) -> None:
    craft = await ajrakh(session)
    contributor = await person(session, "RESEARCHER")
    later = await contributed(
        session, craft, contributor, status="APPROVED", reviewedAt=NOW + timedelta(hours=1)
    )
    first = await contributed(session, craft, contributor, status="APPROVED")
    waiting = await contributed(session, craft, contributor, status="PENDING")
    refused = await contributed(session, craft, contributor, status="REJECTED")
    found = await approved_pictures(session, craft.id)
    assert [picture.contribution_id for picture in found] == [first.id, later.id]
    assert (found[0].mime, found[0].width, found[0].height) == ("image/jpeg", 1200, 800)
    shown = await shown_picture(session, first.id)
    assert shown is not None and (shown.mime, shown.sha256) == ("image/jpeg", first.sha256)
    assert await shown_picture(session, waiting.id) is None
    assert await shown_picture(session, refused.id) is None
    assert await shown_picture(session, uuid.uuid4()) is None


async def test_approving_a_picture_moves_the_stamp_and_places_it_on_the_page(session: AsyncSession) -> None:
    craft = await ajrakh(session)
    contributor, admin = await person(session, "RESEARCHER"), await person(session, "ADMIN")
    before = await page_stamp(session, craft, "OPEN")
    picture = await contributed(
        session,
        craft,
        contributor,
        status="PENDING",
        origin="AI_GENERATED",
        generator=TOOL,
        prompt="A map of the old trade routes",
        claimIds=[history_fact()],
    )
    assert await page_stamp(session, craft, "OPEN") == before
    await images.approve(session, picture.id, admin, None, now=NOW + timedelta(minutes=1))
    await session.flush()
    assert await page_stamp(session, craft, "OPEN") != before
    body = (await served_page(session, craft, "OPEN")).body
    shelves = [
        (chapter["key"], plate)
        for chapter in body["chapters"]
        for item in chapter["items"]
        if (item["part"] or {}).get("kind") == "contributed"
        for plate in item["part"]["pictures"]
    ]
    assert [(key, plate["contributionId"], plate["credit"]) for key, plate in shelves] == [
        ("history", str(picture.id), f"Illustration, made with {TOOL}")
    ]
    assert shelves[0][1]["url"] == f"/api/crafts/contributed/{picture.id}"
    assert str(contributor.id) not in str(body) and contributor.name not in str(body)
