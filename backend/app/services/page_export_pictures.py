from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from urllib.parse import urljoin

from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.component_specs import checked_spec
from app.research.component_specs_plates import PicturePlateSpec, SpecimenPlateSpec
from app.research.component_specs_plates_parts import Picture as ShownPicture
from app.research.licences import open_licence
from app.research.monograph_document import MonographDocument
from app.sources.reference.commons_urls import commons_fitting_width, commons_thumbnail_url

from .export_pictures import Picture, PictureSource, export_pictures
from .page_export_units import PageTexts

__all__ = [
    "MM_PER_INCH",
    "NO_PICTURES",
    "PAGE_PICTURE_SECONDS",
    "PAPER_COLUMN_MM",
    "PAPER_DPI",
    "PICTURE_KINDS",
    "PagePictures",
    "PaperPicture",
    "PlatePicture",
    "copyable",
    "fetched_pictures",
    "paper_url",
    "plate_picture",
    "wanted_pictures",
]

logger = logging.getLogger(__name__)

PAPER_COLUMN_MM = 178.0
MM_PER_INCH = 25.4
PAPER_DPI = 150
PAGE_PICTURE_SECONDS = 10.0
PICTURE_KINDS = frozenset({"picture_plate", "specimen_plate"})
COMMONS_UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"


@dataclass(frozen=True)
class PlatePicture:
    picture: ShownPicture
    credit: str | None


@dataclass(frozen=True)
class PaperPicture:
    id: uuid.UUID
    image_url: str
    src: str


@dataclass(frozen=True)
class PagePictures:
    found: Mapping[str, Picture] = field(default_factory=lambda: MappingProxyType({}))

    def of(self, src: str) -> Picture | None:
        return self.found.get(src)


NO_PICTURES = PagePictures()


def plate_picture(spec: object) -> PlatePicture | None:
    if isinstance(spec, SpecimenPlateSpec):
        return PlatePicture(spec.picture, spec.credit)
    if not isinstance(spec, PicturePlateSpec):
        return None
    if spec.figure is not None:
        return PlatePicture(spec.picture, spec.figure.credit)
    return PlatePicture(spec.picture, spec.opener.credit if spec.opener is not None else None)


def copyable(credit: str) -> bool:
    return open_licence(credit)


def paper_url(picture: ShownPicture, page_url: str) -> str:
    if not picture.src.startswith(COMMONS_UPLOAD):
        return urljoin(page_url, picture.src)
    column = round(PAPER_COLUMN_MM / MM_PER_INCH * PAPER_DPI)
    width = commons_fitting_width(column, picture.width)
    thumb = commons_thumbnail_url(picture.src, width) if width is not None else None
    return thumb or picture.src


def wanted_pictures(
    document: MonographDocument, specs: Mapping[str, Mapping[str, Any]]
) -> list[PaperPicture]:
    texts = PageTexts(document.content)
    wanted: dict[str, PaperPicture] = {}
    for shown in _plates(document, specs):
        if shown.credit is None or not copyable(texts.plain(shown.credit)):
            continue
        url = paper_url(shown.picture, document.page_url)
        wanted.setdefault(
            shown.picture.src, PaperPicture(uuid.uuid5(uuid.NAMESPACE_URL, url), url, shown.picture.src)
        )
    return list(wanted.values())


async def fetched_pictures(
    wanted: list[PaperPicture], source: PictureSource
) -> tuple[PagePictures, frozenset[uuid.UUID]]:
    read = await export_pictures(wanted, source, within=PAGE_PICTURE_SECONDS)
    found = {picture.src: read.found[picture.id] for picture in wanted if picture.id in read.found}
    return PagePictures(MappingProxyType(found)), read.unread


def _plates(document: MonographDocument, specs: Mapping[str, Mapping[str, Any]]) -> Iterator[PlatePicture]:
    for entry in document.content.components:
        spec = specs.get(entry.label)
        if entry.kind not in PICTURE_KINDS or spec is None:
            continue
        try:
            shown = plate_picture(checked_spec(entry.kind, spec))
        except (InvalidInput, ValidationError) as problem:
            logger.warning(
                "the export gives %s by its words: its spec does not parse: %s", entry.label, problem
            )
            continue
        if shown is not None:
            yield shown
