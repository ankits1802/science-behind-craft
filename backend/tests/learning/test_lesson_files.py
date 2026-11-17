import re
from io import BytesIO

from pptx import Presentation
from pypdf import PdfReader

from app.data.export_assets import REVEAL_VERSION
from app.research.explainer_versions import ExplainerVersionDocument
from app.research.export_text import References
from app.research.lesson_words import lesson_words
from app.services.apa_references import apa_references
from app.services.export_files import explainer_citations
from app.services.export_pdfs import explainer_pdf, lesson_pdf
from app.services.lesson_deck import DECK_POLICY, lesson_deck
from app.services.lesson_pptx import lesson_pptx

from ..contracts.learning_golden import VERSIONS, learning
from .lesson_fixtures import golden_pack, pack_references, pictures_of

SLIDE_TITLES = [
    "How is Kutch Ajrakh made, and why does its water matter?",
    "How it is made",
    "How it is made",
    "Why the water matters",
    "The chemistry of the colours",
    *(f"Question {n}" for n in range(1, 10)),
    "Reading list",
    "Sources",
]
FIRST_BULLET = "Outlines where white is required are printed with a carved block and a lime and tree-gum resist paste. [1]"


def shape_texts(slide) -> list[str]:
    return [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]


def test_the_pptx_opens_with_python_pptx_and_holds_the_pack_s_slides() -> None:
    pack = golden_pack()
    deck = Presentation(BytesIO(lesson_pptx(pack, pack_references(pack), pictures_of(pack))))
    slides = list(deck.slides)
    assert [shape_texts(slide)[0] for slide in slides] == SLIDE_TITLES
    section = shape_texts(slides[1])[1].split("\n")
    assert section[0] == f"• {FIRST_BULLET}"
    assert len(section) == 5 and all(re.search(r" \[\d+(, \d+)*\]$", line) for line in section)
    assert sum(1 for shape in slides[1].shapes if shape.shape_type == 13) == 1
    assert not any(shape.shape_type == 13 for shape in slides[2].shapes)
    question = pack.quiz.questions[0]
    assert shape_texts(slides[5])[1].split("\n") == [
        question.prompt,
        *(f"{chr(65 + n)}. {o.text}" for n, o in enumerate(question.options)),
    ]
    key = question.options[question.answer]
    assert slides[5].notes_slide.notes_text_frame.text.startswith(
        f"Answers: {chr(65 + question.answer)}. {key.text}"
    )
    sources = shape_texts(slides[-1])[1].split("\n")
    assert [line.split(" ", 1)[0] for line in sources] == [f"[{n}]" for n in range(1, len(pack.sources) + 1)]


def test_every_pptx_bullet_carries_the_numbers_of_its_own_sources() -> None:
    pack = golden_pack()
    refs = pack_references(pack)
    deck = Presentation(BytesIO(lesson_pptx(pack, refs, {})))
    shown = [line for slide in list(deck.slides)[1:5] for line in shape_texts(slide)[1].split("\n")]
    bullets = [sentence for slide in pack.slides for sentence in slide.bullets]
    numbers = {source.id: n for n, source in enumerate(pack.sources, 1)}
    for line, sentence in zip(shown, bullets, strict=True):
        cited = sorted({numbers[c.source_id] for c in sentence.citations})
        assert line == f"• {sentence.text} [{', '.join(map(str, cited))}]"


def test_a_picture_that_could_not_be_read_is_left_out_with_its_credit() -> None:
    pack = golden_pack()
    deck = Presentation(BytesIO(lesson_pptx(pack, pack_references(pack), {})))
    first = list(deck.slides)[1]
    assert not any(shape.shape_type == 13 for shape in first.shapes)
    assert all("SMarndi" not in text for text in shape_texts(first))
    html = lesson_deck(pack, pack_references(pack), {}).decode("utf-8")
    assert "<figure>" not in html and "SMarndi" not in html


def test_the_html_deck_is_one_offline_file_with_reveal_and_every_slide() -> None:
    pack = golden_pack()
    html = lesson_deck(pack, pack_references(pack), pictures_of(pack)).decode("utf-8")
    assert html.count("<section ") == len(pack.slides)
    assert re.findall(r'data-kind="([A-Z]+)"', html) == [slide.kind for slide in pack.slides]
    assert f'content="{DECK_POLICY}"' in html and "img-src data:" in DECK_POLICY
    assert (
        f"reveal.js {REVEAL_VERSION}" in html
        and "MIT licensed" in html
        and "Permission is hereby granted" in html
    )
    assert html.count("<script>") == 2 and "<script src" not in html and "<link" not in html
    assert html.count('src="data:image/jpeg;base64,') == 1
    assert "Ajrak Printing Materials 1 · SMarndi · CC BY-SA 4.0 · https://commons.wikimedia.org/" in html
    assert f'{FIRST_BULLET[:-4]} <span class="kv-cite">[1]</span>' in html


def test_the_lesson_pdf_has_a_page_per_slide_then_the_answers() -> None:
    pack = golden_pack()
    reader = PdfReader(BytesIO(lesson_pdf(pack, pack_references(pack), pictures_of(pack))))
    assert len(reader.pages) == len(pack.slides) + 1
    first_section = " ".join(reader.pages[1].extract_text().split())
    assert "How it is made" in first_section and FIRST_BULLET in first_section
    answers = " ".join(reader.pages[-1].extract_text().split())
    first = pack.quiz.questions[0]
    assert answers.startswith("Answers") and f"1. {chr(65 + first.answer)}. resist paste" in answers
    assert reader.metadata.title == pack.title


def test_the_explainer_pdf_shows_the_version_with_numbered_citations_and_sources() -> None:
    document = ExplainerVersionDocument.model_validate(learning(VERSIONS)["latest"])
    export = explainer_citations(document, {}, apa_references)
    reader = PdfReader(BytesIO(explainer_pdf(document, References(tuple(export.entries)), {})))
    text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
    assert text.startswith(document.mark.question)
    assert "Kutch Ajrakh · v2 · 2026-11-18" in text
    for section in document.explainer.sections:
        assert section.title in text
    assert lesson_words("en").sources in text
    for entry in export.entries:
        assert f"[{entry.number}]" in text


def test_a_hindi_pdf_is_written_in_its_own_script() -> None:
    pack = golden_pack()
    hindi = pack.model_copy(update={"language": "hi", "title": "अजरख कैसे बनता है?"})
    reader = PdfReader(BytesIO(lesson_pdf(hindi, pack_references(pack), {})))
    fonts = reader.pages[0]["/Resources"]["/Font"]
    names = {str(fonts[name].get_object()["/BaseFont"]) for name in fonts}
    assert len(reader.pages) == len(pack.slides) + 1
    assert any("NotoSansDevanagari" in name for name in names)
