import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.research.craft_page import PagePicture
from app.research.media_refs import MediaRef
from app.services.chapter_plates import PicturePlan, picture_plan


def linked_picture() -> PagePicture:
    media = MediaRef(
        id=uuid.UUID(int=5),
        display="LINK_CARD",
        provider="curation",
        page_url="https://example.org/print",
        image_url="https://example.org/print.jpg",
        width=None,
        height=None,
        title="A block print",
        alt="A block print",
        author=None,
        site="example.org",
        credit=None,
        licence=None,
        licence_url=None,
        source_id=None,
        retrieved_at=datetime(2026, 11, 19, tzinfo=UTC),
    )
    return PagePicture(
        media=media, caption="A block print", role="HERO", stage_id=None, claim_ids=[uuid.UUID(int=6)]
    )


def test_a_picture_shown_only_as_a_link_card_becomes_no_plate_and_no_masthead() -> None:
    context: Any = SimpleNamespace(records=SimpleNamespace(curated=None))
    assert picture_plan(context, [linked_picture()]) == PicturePlan(None, ())
