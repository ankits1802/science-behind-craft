import zipfile
from datetime import date
from io import BytesIO

from app.data.interface_words import Review, WordEntry
from app.services.interface_words import reviewed_of
from app.services.page_export_document import export_specs, page_export
from app.services.page_export_docx import page_docx
from app.services.page_export_pictures import NO_PICTURES
from app.services.page_export_words import (
    DRAWN,
    ENGLISH_EXPORT_WORDS,
    EXPORT_WORDS,
    PICTURE,
    SOURCES,
    ExportWords,
    kind_word,
)

from .page_fixture import FIXTURE_LABELS, fixture_page
from .picture_fixture import picture_page

READER = Review("A reader of Hindi", date(2026, 11, 30))
HEADING_TEXT, LABEL_TEXT, DRAWN_TEXT = "स्रोत", "चित्र", "बनाया"
ENGLISH_MARK = '<w:lang w:val="en" w:bidi="en"/>'


def entry(key: str, english: str, text: str, review: Review | None = READER) -> WordEntry:
    return WordEntry(key=key, english=english, text=text, source="a test source", review=review)


def hindi_words(*entries: WordEntry) -> ExportWords:
    return ExportWords(reviewed_of("hi", entries))


def test_a_reviewed_word_is_drawn_in_its_language_and_an_unreviewed_one_in_english() -> None:
    words = hindi_words(
        entry("export.heading", "Sources", HEADING_TEXT), entry("export.label", "Picture", LABEL_TEXT, None)
    )
    assert (words.said(SOURCES), words.lang(SOURCES)) == (HEADING_TEXT, None)
    assert (words.said(PICTURE), words.lang(PICTURE)) == ("Picture", "en")


def test_a_reviewed_word_whose_english_is_no_longer_the_code_s_is_drawn_in_english() -> None:
    words = hindi_words(entry("export.heading", "Source list", HEADING_TEXT))
    assert (words.said(SOURCES), words.lang(SOURCES)) == ("Sources", "en")


def test_english_pages_draw_the_code_s_english_unmarked() -> None:
    assert [ENGLISH_EXPORT_WORDS.said(word) for word in (SOURCES, PICTURE)] == ["Sources", "Picture"]
    assert ENGLISH_EXPORT_WORDS.lang(SOURCES) is None
    assert ENGLISH_EXPORT_WORDS.said(kind_word("molecule_3d")) == "Molecule in 3D"
    assert ENGLISH_EXPORT_WORDS.said(kind_word("picture_plate")) == "Picture plate"


def test_a_hindi_word_document_draws_its_reviewed_heading_and_marks_its_english_words() -> None:
    page = picture_page().model_copy(update={"language": "hi"})
    words = hindi_words(entry("export.heading", "Sources", HEADING_TEXT))
    data = page_docx(page_export(page, export_specs(page), pictures=NO_PICTURES, words=words))
    with zipfile.ZipFile(BytesIO(data)) as package:
        document = package.read("word/document.xml").decode("utf-8")
    assert (
        f'<w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t xml:space="preserve">{HEADING_TEXT}</w:t>' in document
    )
    assert f'{ENGLISH_MARK}</w:rPr><w:t xml:space="preserve">Picture: </w:t>' in document


def test_a_figure_s_fixed_label_follows_the_words_it_is_given() -> None:
    page = fixture_page()
    words = hindi_words(entry("export.label", "Drawn", DRAWN_TEXT))
    export = page_export(page, page.specs, words=words)
    figure = next(shown for shown in export.figures() if shown.label == FIXTURE_LABELS["diagram_kit"])
    assert any(line.plain.startswith(f"{DRAWN_TEXT}: Zinc-white alloy") for line in figure.lines)
    assert not any(line.plain.startswith("Drawn: ") for line in figure.lines)


def test_the_reviewed_export_words_are_part_of_what_a_file_is_made_from() -> None:
    words = hindi_words(
        entry("export.heading", "Sources", HEADING_TEXT), entry("essay.actions", "Save", "सहेजें")
    )
    assert words.made_from() == [["export.heading", "Sources", HEADING_TEXT]]
    assert ENGLISH_EXPORT_WORDS.made_from() == []


def test_every_export_word_has_one_key_and_english_and_a_dotted_export_key() -> None:
    pairs = [(word.key, word.english) for word in EXPORT_WORDS]
    assert len(pairs) == len(set(pairs))
    assert all(word.key.startswith("export.") for word in EXPORT_WORDS)
    assert (DRAWN.key, DRAWN.english) in pairs and (SOURCES.key, SOURCES.english) in pairs
