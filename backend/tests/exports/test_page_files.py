import asyncio
import zipfile
from datetime import UTC, datetime
from functools import cache
from io import BytesIO
from xml.etree import ElementTree

from pypdf import PdfReader

from app.research.export_links import EXPORT_MEDIA_TYPES
from app.services.apa_references import apa_references
from app.services.export_files import ExportTools
from app.services.page_export_document import export_specs, page_export
from app.services.page_export_docx import page_docx
from app.services.page_export_files import PAGE_EXPORT_OWNER, page_export_link
from app.services.page_export_model import PageExport
from app.services.page_export_pdf import page_pdf

from ..learning.lesson_fixtures import FakeBucket
from .page_fixture import fixture_export, fixture_page, kutch_document

NOW = datetime(2026, 11, 25, 6, 30, tzinfo=UTC)
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCX_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "docProps/core.xml",
    "word/styles.xml",
    "word/_rels/document.xml.rels",
    "word/document.xml",
}
FIGURE_TITLES = (
    "Where bidri was made, from Bidar to Lucknow",
    "From zinc-white to black",
    "What if, for bidri",
    "Bidriware's GI registration",
    "Which bath blackens the alloy?",
)


class _NoPictures:
    async def picture(self, url: str) -> bytes:
        raise AssertionError(f"a page export reads no picture: {url}")


def pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return " ".join(" ".join(page.extract_text() for page in reader.pages).split())


def line_ops(data: bytes) -> int:
    streams = (page.get_contents() for page in PdfReader(BytesIO(data)).pages)
    return sum(stream.get_data().count(b" l") for stream in streams if stream is not None)


def word_paragraphs(data: bytes) -> list[str]:
    with zipfile.ZipFile(BytesIO(data)) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    return [
        "".join(node.text or "" for node in paragraph.iter(f"{WORD}t")) for paragraph in root.iter(f"{WORD}p")
    ]


@cache
def kutch_export() -> PageExport:
    document = kutch_document()
    return page_export(document, export_specs(document))


def test_the_pdf_holds_every_new_kind_s_title_lines_note_credits_and_drawings() -> None:
    data = page_pdf(fixture_export())
    text = pdf_text(data)
    assert text.startswith("Every new kind")
    for title in (*FIGURE_TITLES, "Sources"):
        assert title in text, title
    assert "1. Bidar (this craft's place)" in text and "Key: Nitrogen; Hydrogen; Chlorine" in text
    assert "On the page the reader turns and zooms the model; here it is drawn as it rests." in text
    assert "For reference only" in text
    assert line_ops(data) > 2000


def test_the_word_document_holds_its_parts_one_picture_per_still_and_every_line() -> None:
    export = fixture_export()
    data = page_docx(export)
    with zipfile.ZipFile(BytesIO(data)) as package:
        names = set(package.namelist())
        document = package.read("word/document.xml").decode("utf-8")
    stills = sum(len(figure.stills) for figure in export.figures())
    assert stills == 11
    assert names >= DOCX_PARTS and {f"word/media/figure{n}.png" for n in range(1, stills + 1)} <= names
    assert document.count("<w:drawing>") == stills
    paragraphs = word_paragraphs(data)
    assert paragraphs[0] == "Every new kind"
    for title in FIGURE_TITLES:
        assert title in paragraphs, title
    assert "Ammonium chloride · NH4Cl · PubChem CID 25517" in paragraphs
    assert '<w:vertAlign w:val="subscript"/>' in document
    references = [paragraph for paragraph in paragraphs if paragraph.startswith("[")]
    assert len(references) == len(export.references)


def test_kutch_ajrakh_exports_to_a_pdf_and_a_word_document_that_open() -> None:
    export = kutch_export()
    text = pdf_text(page_pdf(export))
    assert text.startswith("Kutch Ajrakh") and "The chemistry" in text and "Sources" in text
    paragraphs = word_paragraphs(page_docx(export))
    assert "The chemistry" in paragraphs and paragraphs.count("Sources") >= 1


async def test_a_page_export_is_filed_once_under_its_page_and_named_by_the_naming_rule() -> None:
    bucket = FakeBucket()
    tools = ExportTools(
        objects=bucket,
        pictures=_NoPictures(),
        apa=apa_references,
        clock=lambda: NOW,
        builds=asyncio.Semaphore(1),
    )
    document = fixture_page()
    link = await page_export_link(tools, document, served="v1-abc", fmt="docx")
    again = await page_export_link(tools, document, served="v1-abc", fmt="docx")
    assert link == again and link.format == "docx"
    assert link.file_name == "KalaVigyan_Craft-Page_2026-11-25_Every-New-Kind_Export_v1.docx"
    [key] = bucket.stored
    assert key.startswith(f"exports/{PAGE_EXPORT_OWNER}/") and key.endswith(link.file_name)
    assert bucket.stored[key][1] == EXPORT_MEDIA_TYPES["docx"]
    assert bucket.stored[key][0].startswith(b"PK")
