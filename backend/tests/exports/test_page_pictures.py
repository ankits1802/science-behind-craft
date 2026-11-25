import asyncio
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from xml.etree import ElementTree

import pytest
from pypdf import PdfReader

from app.core.errors import ExternalFailure
from app.research.component_specs_plates_parts import Picture as ShownPicture
from app.services.apa_references import apa_references
from app.services.export_files import ExportTools
from app.services.export_pictures import PictureSource, export_pictures
from app.services.page_export_document import export_specs, page_export
from app.services.page_export_docx import page_docx
from app.services.page_export_files import page_export_link
from app.services.page_export_model import ExportFigure, PageExport
from app.services.page_export_pdf import page_pdf
from app.services.page_export_pictures import (
    NO_PICTURES,
    PaperPicture,
    copyable,
    paper_url,
    wanted_pictures,
)
from app.services.page_export_words import PICTURE_CLOSED, PICTURE_UNREAD

from ..learning.lesson_fixtures import FakeBucket, picture_bytes
from .page_fixture import kutch_document
from .picture_fixture import (
    CAPTION,
    COMMONS_CLOTH,
    OPEN_CREDIT,
    PAGE_URL,
    PICTURE_ALT,
    PICTURE_LABEL,
    found,
    picture_page,
)

NOW = datetime(2026, 11, 25, 6, 30, tzinfo=UTC)
THUMB = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Printed_cloth.jpg/{width}px-Printed_cloth.jpg"
)
CLOSED_CREDITS = (
    "Photo: A. Printer, CC BY-NC 4.0, via Flickr",
    "Photo: A. Printer, CC BY-ND 4.0, via Flickr",
    "Photo: A. Printer, all rights reserved",
    "Contributed to KalaVigyan",
)
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class Pictures:
    def __init__(self) -> None:
        self.asked: list[str] = []

    async def picture(self, url: str) -> bytes:
        self.asked.append(url)
        return picture_bytes("PNG", (1280, 960))


class Refusing:
    async def picture(self, url: str) -> bytes:
        raise ExternalFailure("picture_files answered 404", service="picture_files")


class Stalling:
    async def picture(self, url: str) -> bytes:
        await asyncio.sleep(5)
        return picture_bytes()


def plate(export: PageExport) -> ExportFigure:
    return next(shown for shown in export.figures() if shown.label == PICTURE_LABEL)


def shown(width: int, src: str = COMMONS_CLOTH) -> ShownPicture:
    return ShownPicture(src=src, width=width, height=width * 3 // 4, alt=PICTURE_ALT)


def word_paragraphs(data: bytes) -> list[str]:
    with zipfile.ZipFile(BytesIO(data)) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    return ["".join(node.text or "" for node in p.iter(f"{WORD}t")) for p in root.iter(f"{WORD}p")]


@pytest.mark.parametrize(
    ("width", "url"),
    [
        (4000, THUMB.format(width=1280)),
        (1280, THUMB.format(width=1280)),
        (1000, THUMB.format(width=960)),
        (800, THUMB.format(width=500)),
        (300, COMMONS_CLOTH),
    ],
)
def test_a_commons_picture_is_read_at_the_standard_width_that_fits_the_paper_column(
    width: int, url: str
) -> None:
    assert paper_url(shown(width), PAGE_URL) == url


def test_a_picture_the_site_serves_itself_is_read_from_the_page_s_own_site() -> None:
    local = shown(1280, "/monographs/kutch-ajrakh/img/ajrakh-cloth-field-and-borders.jpg")
    assert paper_url(local, PAGE_URL) == (
        "https://kalavigyan.example/monographs/kutch-ajrakh/img/ajrakh-cloth-field-and-borders.jpg"
    )


def test_a_shown_picture_is_embedded_with_its_caption_first_and_its_credit_after() -> None:
    page = picture_page()
    figure = plate(page_export(page, export_specs(page), pictures=found()))
    assert [(picture.alt, picture.picture.width) for picture in figure.pictures] == [(PICTURE_ALT, 1280)]
    assert [line.plain for line in figure.lines] == [CAPTION]
    assert figure.credits == (OPEN_CREDIT,) and figure.note is None
    paragraphs = word_paragraphs(page_docx(page_export(page, export_specs(page), pictures=found())))
    assert paragraphs.index(CAPTION) < paragraphs.index(OPEN_CREDIT)


def test_the_word_document_holds_the_picture_as_a_jpeg_and_the_pdf_draws_it() -> None:
    page = picture_page()
    export = page_export(page, export_specs(page), pictures=found())
    with zipfile.ZipFile(BytesIO(page_docx(export))) as package:
        names = set(package.namelist())
        types = package.read("[Content_Types].xml").decode("utf-8")
        document = package.read("word/document.xml").decode("utf-8")
    assert "word/media/figure1.jpeg" in names and 'Extension="jpeg" ContentType="image/jpeg"' in types
    assert f'descr="{PICTURE_ALT}"' in document
    [first] = PdfReader(BytesIO(page_pdf(export))).pages
    assert len(first.images) == 1


def test_a_picture_that_did_not_arrive_is_given_by_its_alt_text_and_credit_and_says_so() -> None:
    page = picture_page()
    figure = plate(page_export(page, export_specs(page), pictures=NO_PICTURES))
    assert figure.pictures == ()
    assert [line.plain for line in figure.lines] == [CAPTION, f"Picture: {PICTURE_ALT}"]
    assert figure.credits == (OPEN_CREDIT,) and figure.note == PICTURE_UNREAD.english


@pytest.mark.parametrize("credit", CLOSED_CREDITS)
def test_a_picture_whose_licence_forbids_a_copy_is_neither_read_nor_embedded(credit: str) -> None:
    page = picture_page(credit=credit)
    assert not copyable(credit)
    assert wanted_pictures(page, export_specs(page)) == []
    figure = plate(page_export(page, export_specs(page), pictures=found()))
    assert figure.pictures == () and figure.note == PICTURE_CLOSED.english
    assert f"Picture: {PICTURE_ALT}" in [line.plain for line in figure.lines]


def test_an_open_picture_is_asked_for_once_by_its_paper_address() -> None:
    page = picture_page()
    [wanted] = wanted_pictures(page, export_specs(page))
    assert (wanted.image_url, wanted.src) == (THUMB.format(width=1280), COMMONS_CLOTH)


def test_kutch_ajrakh_asks_for_its_nine_plates_and_its_specimen_from_its_own_site() -> None:
    document = kutch_document()
    wanted = wanted_pictures(document, export_specs(document))
    assert len(wanted) == 10
    assert all(
        one.image_url.startswith("https://kalavigyan.example/monographs/kutch-ajrakh/img/") for one in wanted
    )
    assert len({one.src for one in wanted}) == 10


async def test_a_picture_that_takes_too_long_is_left_unread() -> None:
    wanted: list[PaperPicture] = _wanted()
    read = await export_pictures(wanted, Stalling(), within=0.05)
    assert read.found == {} and read.unread == frozenset(one.id for one in wanted)


async def test_the_export_reads_the_shown_picture_and_files_apart_one_it_could_not_read() -> None:
    bucket, pictures = FakeBucket(), Pictures()
    page = picture_page()
    link = await page_export_link(_tools(bucket, pictures), page, served="v1-abc", fmt="docx")
    assert pictures.asked == [THUMB.format(width=1280)] and link.format == "docx"
    [(body, _)] = bucket.stored.values()
    with zipfile.ZipFile(BytesIO(body)) as package:
        assert "word/media/figure1.jpeg" in package.namelist()
    refused = FakeBucket()
    await page_export_link(_tools(refused, Refusing()), page, served="v1-abc", fmt="docx")
    assert set(refused.stored) != set(bucket.stored)


def _wanted() -> list[PaperPicture]:
    page = picture_page()
    return wanted_pictures(page, export_specs(page))


def _tools(bucket: FakeBucket, pictures: PictureSource) -> ExportTools:
    return ExportTools(
        objects=bucket, pictures=pictures, apa=apa_references, clock=lambda: NOW, builds=asyncio.Semaphore(1)
    )
