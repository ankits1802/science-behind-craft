from typing import Any

from app.research.monograph_document import MonographDocument
from app.research.monograph_page import ComponentEntry, LayoutEntry, MonographContent, TextUnit
from app.services.export_pictures import Picture, normalised
from app.services.page_export_pictures import PagePictures

from ..learning.lesson_fixtures import picture_bytes

__all__ = [
    "CAPTION",
    "COMMONS_CLOTH",
    "OPEN_CREDIT",
    "PAGE_URL",
    "PICTURE_ALT",
    "PICTURE_LABEL",
    "found",
    "picture_page",
    "shown_picture",
]

PAGE_URL = "https://kalavigyan.example/crafts/Paper-Test-Craft"
PICTURE_LABEL = "paper-test-craft/design/printed-cloth-photo"
COMMONS_CLOTH = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Printed_cloth.jpg"
CAPTION = "A printed cloth held up to show its border."
OPEN_CREDIT = "Photo: A. Printer, CC BY-SA 4.0, via Wikimedia Commons"
PICTURE_ALT = "Two printers hold up a printed cloth."
LEDE = "u0001"
CAPTION_UNIT, CREDIT_UNIT = "u0002", "u0003"


def shown_picture() -> Picture:
    picture = normalised(picture_bytes("PNG", (1280, 960)))
    assert picture is not None
    return picture


def found(src: str = COMMONS_CLOTH) -> PagePictures:
    return PagePictures({src: shown_picture()})


def picture_page(
    *, credit: str = OPEN_CREDIT, src: str = COMMONS_CLOTH, width: int = 4000, subject: str = "craft"
) -> MonographDocument:
    units = {
        LEDE: _unit("opening", "Printers block print cloth by hand."),
        CAPTION_UNIT: _unit("design", CAPTION),
        CREDIT_UNIT: _unit("design", credit),
    }
    layout = [
        LayoutEntry(chapter="opening", kind="unit", ref=LEDE),
        LayoutEntry(chapter="design", kind="component", ref=PICTURE_LABEL),
        LayoutEntry(chapter="design", kind="unit", ref=CAPTION_UNIT, within=PICTURE_LABEL),
        LayoutEntry(chapter="design", kind="unit", ref=CREDIT_UNIT, within=PICTURE_LABEL),
    ]
    content = MonographContent(
        craft_slug="Paper-Test-Craft",
        sources={},
        citations={},
        citation_claims={},
        data={},
        units=units,
        components=[_plate()],
        layout=layout,
    )
    return MonographDocument(
        subject_kind=subject,
        subject_slug="Paper-Test-Craft",
        title="Paper test craft",
        version=1,
        content=content,
        specs={PICTURE_LABEL: _spec(src, width)},
        page_url=PAGE_URL,
    )


def _unit(chapter: str, text: str) -> TextUnit:
    return TextUnit(chapter=chapter, tag="p", field="DESIGN", nodes=[text], claim_ids=[])


def _plate() -> ComponentEntry:
    return ComponentEntry(
        label=PICTURE_LABEL,
        chapter="design",
        anchor="#printed-cloth",
        kind="picture_plate",
        title="A printed cloth",
        description="A photograph of a printed cloth.",
        field="DESIGN",
        fields=[],
        subjects=[],
    )


def _spec(src: str, width: int) -> dict[str, Any]:
    return {
        "setting": "figure",
        "picture": {"src": src, "width": width, "height": width * 3 // 4, "alt": PICTURE_ALT},
        "figure": {"classes": ["plate"], "captions": [{"unit": CAPTION_UNIT}], "credit": CREDIT_UNIT},
    }
