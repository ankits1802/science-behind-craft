from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.slide import Slide as DeckSlide
from pptx.text.text import TextFrame, _Paragraph
from pptx.util import Emu, Inches, Pt

from app.core.clock import INDIA_TZ
from app.research.citation_export import CitationEntry
from app.research.export_text import CREDIT_SEPARATOR, References, picture_credit, reference_link
from app.research.lesson_words import lesson_words
from app.research.lessons import LessonPack, Slide
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS, RIGHT_TO_LEFT_SCRIPTS

from .export_pictures import Picture

__all__ = ["BLANK_LAYOUT", "lesson_pptx"]

BLANK_LAYOUT = 6
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
MARGIN = Inches(0.6)
TITLE_TOP = Inches(0.4)
TITLE_HEIGHT = Inches(1.1)
BODY_TOP = Inches(1.6)
PICTURE_WIDTH = Inches(4.4)
CREDIT_HEIGHT = Inches(0.9)
GAP = Inches(0.3)
INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x4B, 0x55, 0x63)
ACCENT = RGBColor(0x5B, 0x21, 0xB6)
BODY_SIZES = ((450, 20), (800, 16), (1200, 13))
SMALLEST_SIZE = 11
BULLET = "• "


@dataclass(frozen=True)
class _Deck:
    pack: LessonPack
    refs: References
    pictures: Mapping[uuid.UUID, Picture]
    right_to_left: bool


def lesson_pptx(pack: LessonPack, refs: References, pictures: Mapping[uuid.UUID, Picture]) -> bytes:
    script = ANSWER_LANGUAGE_SPECS[pack.language].script
    deck = _Deck(pack, refs, pictures, script in RIGHT_TO_LEFT_SCRIPTS)
    presentation = Presentation()
    presentation.slide_width = SLIDE_WIDTH
    presentation.slide_height = SLIDE_HEIGHT
    layout = presentation.slide_layouts[BLANK_LAYOUT]
    for slide in pack.slides:
        _draw(presentation.slides.add_slide(layout), slide, deck)
    out = BytesIO()
    presentation.save(out)
    return out.getvalue()


def _draw(page: DeckSlide, slide: Slide, deck: _Deck) -> None:
    if slide.kind == "TITLE":
        _title_slide(page, slide, deck)
        return
    _write(_box(page, TITLE_TOP, TITLE_HEIGHT), [slide.title], deck, size=30, colour=ACCENT, bold=True)
    if slide.kind == "SECTION":
        _section(page, slide, deck)
    elif slide.kind == "QUIZ":
        _question(page, slide, deck)
    elif slide.kind == "READING":
        _references(page, (deck.refs.of_source(item.source.id) for item in deck.pack.reading_list), deck)
    else:
        _references(page, (deck.refs.of_source(source.id) for source in deck.pack.sources), deck)


def _title_slide(page: DeckSlide, slide: Slide, deck: _Deck) -> None:
    pack = deck.pack
    made = pack.created_at.astimezone(INDIA_TZ).date().isoformat()
    meta = CREDIT_SEPARATOR.join(part for part in (pack.craft.name if pack.craft else None, made) if part)
    _write(_box(page, Inches(2.4), Inches(2.0)), [slide.title], deck, size=40, colour=ACCENT, bold=True)
    _write(_box(page, Inches(4.6), Inches(0.8)), [meta], deck, size=18, colour=MUTED)


def _section(page: DeckSlide, slide: Slide, deck: _Deck) -> None:
    picture = deck.pictures.get(slide.image.id) if slide.image is not None else None
    width = SLIDE_WIDTH - 2 * MARGIN - ((PICTURE_WIDTH + GAP) if picture is not None else 0)
    lines = [f"{BULLET}{s.text} {deck.refs.sentence_marker(s)}" for s in slide.bullets]
    frame = _box(page, BODY_TOP, SLIDE_HEIGHT - BODY_TOP - MARGIN, width=width)
    _write(frame, lines, deck, size=_body_size(lines))
    if slide.image is None or picture is None:
        return
    left = SLIDE_WIDTH - MARGIN - PICTURE_WIDTH
    room = SLIDE_HEIGHT - BODY_TOP - MARGIN - CREDIT_HEIGHT
    height = min(Emu(int(PICTURE_WIDTH * picture.height / picture.width)), room)
    shown_width = Emu(int(height * picture.width / picture.height))
    page.shapes.add_picture(BytesIO(picture.data), left, BODY_TOP, width=shown_width, height=height)
    credit = _box(page, Emu(BODY_TOP + height + Inches(0.1)), CREDIT_HEIGHT, left=left, width=PICTURE_WIDTH)
    _write(credit, [picture_credit(slide.image)], deck, size=10, colour=MUTED)


def _question(page: DeckSlide, slide: Slide, deck: _Deck) -> None:
    quiz = deck.pack.quiz
    if quiz is None or slide.question is None:
        raise ValueError(f"slide {slide.number} asks a question the lesson does not hold")
    question = quiz.questions[slide.question]
    options = [f"{chr(ord('A') + n)}. {option.text}" for n, option in enumerate(question.options)]
    frame = _box(page, BODY_TOP, SLIDE_HEIGHT - BODY_TOP - MARGIN)
    _write(frame, [question.prompt, *options], deck, size=_body_size([question.prompt, *options]) + 2)
    key = question.options[question.answer]
    words = lesson_words(deck.pack.language)
    page.notes_slide.notes_text_frame.text = (
        f"{words.answers}: {chr(ord('A') + question.answer)}. {key.text}\n"
        f"{key.sentence.text} {deck.refs.sentence_marker(key.sentence)}"
    )


def _references(page: DeckSlide, entries: Iterable[CitationEntry], deck: _Deck) -> None:
    listed = list(entries)
    lines = [f"[{entry.number}] {entry.apa}" for entry in listed]
    frame = _box(page, BODY_TOP, SLIDE_HEIGHT - BODY_TOP - MARGIN)
    _write(frame, lines, deck, size=_body_size(lines) - 2, links=[reference_link(e) for e in listed])


def _box(
    page: DeckSlide, top: int, height: int, *, left: int = MARGIN, width: int | None = None
) -> TextFrame:
    shape = page.shapes.add_textbox(left, top, width or SLIDE_WIDTH - 2 * MARGIN, height)
    frame = shape.text_frame
    frame.word_wrap = True
    return frame


def _write(
    frame: TextFrame,
    lines: Sequence[str],
    deck: _Deck,
    *,
    size: int,
    colour: RGBColor = INK,
    bold: bool = False,
    links: Sequence[str | None] = (),
) -> None:
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        _direct(paragraph, deck.right_to_left)
        paragraph.space_after = Pt(size * 0.4)
        run = paragraph.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = colour
        link = links[index] if index < len(links) else None
        if link:
            run.hyperlink.address = link


def _direct(paragraph: _Paragraph, right_to_left: bool) -> None:
    if not right_to_left:
        return
    paragraph.alignment = PP_ALIGN.RIGHT
    paragraph._p.get_or_add_pPr().set("rtl", "1")


def _body_size(lines: Sequence[str]) -> int:
    characters = sum(len(line) for line in lines)
    return next((size for limit, size in BODY_SIZES if characters <= limit), SMALLEST_SIZE)
