import uuid

import pytest

from app.research.citations import cited_source_ids
from app.research.lesson_builder import (
    TOO_MANY_SLIDES_DETAIL,
    LessonNotBuildable,
    UnknownLessonSection,
    lesson_pack,
    lesson_title,
)
from app.research.lessons import LESSON_BULLETS_MAX, LessonRequest

from ..contracts.learning_golden import LESSON, learning
from .lesson_fixtures import BUILT_AT, first_version, golden_pack, golden_request, visible_claims

PACK_ID = uuid.UUID(learning(LESSON)["pack"]["id"])
WITHDRAWN = "8e106f5b-6c6e-5857-9d66-95ec73a07421"


def built(request: LessonRequest | None = None, visible: frozenset[str] | None = None):
    document = first_version()
    return lesson_pack(
        document,
        request or golden_request(),
        visible_claim_ids=visible if visible is not None else visible_claims(document),
        pack_id=PACK_ID,
        created_at=BUILT_AT,
    )


def test_a_pack_built_from_the_document_golden_is_the_lesson_fixture() -> None:
    assert built().model_dump(mode="json", by_alias=True) == learning(LESSON)["pack"]


def test_every_slide_fact_is_an_explainer_sentence_with_its_citations() -> None:
    document = first_version()
    stored = {
        sentence.id: sentence
        for section in document.explainer.sections
        for block in section.blocks
        for sentence in block.cited_sentences()
    }
    pack = built()
    bullets = [sentence for slide in pack.slides for sentence in slide.bullets]
    assert bullets and all(sentence.citations for sentence in bullets)
    assert all(sentence == stored[sentence.id] for sentence in bullets)
    assert all(len(slide.bullets) <= LESSON_BULLETS_MAX for slide in pack.slides)
    keyed = [question.options[question.answer].sentence for question in pack.quiz.questions]
    assert all(sentence.citations for sentence in keyed)


def test_the_reading_list_is_the_explainer_s_cited_sources_and_nothing_else() -> None:
    pack = built()
    document = first_version()
    shown = [s for slide in pack.slides for s in slide.bullets] + list(pack.quiz.cited_sentences())
    assert [source.id for source in pack.sources] == cited_source_ids(shown)
    assert {item.source.id for item in pack.reading_list} == {source.id for source in pack.sources}
    assert {source.id for source in pack.sources} <= {source.id for source in document.explainer.sources}
    explainer_sources = {source.id: source for source in document.explainer.sources}
    assert all(item.source == explainer_sources[item.source.id] for item in pack.reading_list)


def test_a_withdrawn_claim_is_never_taught() -> None:
    document = first_version()
    pack = built(visible=visible_claims(document) - {WITHDRAWN})
    taught = [s for slide in pack.slides for s in slide.bullets] + list(pack.quiz.cited_sentences())
    assert all(WITHDRAWN not in {c.claim_id for c in sentence.citations} for sentence in taught)
    assert len([s for slide in pack.slides for s in slide.bullets]) == 11


def test_a_lesson_without_its_quiz_runs_title_sections_reading_and_sources() -> None:
    pack = built(golden_request().model_copy(update={"quiz": False}))
    assert pack.quiz is None
    assert [slide.kind for slide in pack.slides] == ["TITLE", *["SECTION"] * 4, "READING", "SOURCES"]
    assert [item.cited_by for item in pack.reading_list] == [9, 1, 1, 1, 1]


def test_sections_are_taught_in_the_order_chosen() -> None:
    pack = built(golden_request().model_copy(update={"section_ids": ["s3", "s1"], "quiz": False}))
    assert [slide.section_id for slide in pack.slides if slide.kind == "SECTION"] == ["s3", "s1", "s1"]
    assert pack.slides[2].image is not None and pack.slides[3].image is None


def test_a_section_the_version_lacks_is_unknown_and_an_unfinished_one_is_refused() -> None:
    with pytest.raises(UnknownLessonSection):
        built(golden_request().model_copy(update={"section_ids": ["s9"]}))
    document = first_version()
    empty = document.explainer.sections[2].model_copy(
        update={"state": "EMPTY", "blocks": [], "searched": "x"}
    )
    sections = [*document.explainer.sections[:2], empty]
    unfinished = document.model_copy(
        update={"explainer": document.explainer.model_copy(update={"sections": sections})}
    )
    with pytest.raises(LessonNotBuildable, match="finished sections"):
        lesson_pack(
            unfinished,
            golden_request(),
            visible_claim_ids=visible_claims(document),
            pack_id=PACK_ID,
            created_at=BUILT_AT,
        )


def test_a_lesson_with_nothing_left_to_teach_is_refused() -> None:
    with pytest.raises(LessonNotBuildable, match="cited sentence left"):
        built(visible=frozenset())


def test_a_lesson_never_runs_past_sixty_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.research import lesson_builder

    monkeypatch.setattr(lesson_builder, "LESSON_SLIDES_MAX", 15)
    with pytest.raises(LessonNotBuildable) as refused:
        built()
    assert refused.value.detail == TOO_MANY_SLIDES_DETAIL


def test_a_long_question_is_cut_at_a_word_into_a_title() -> None:
    question = "Why " + "very " * 30 + "long?"
    assert lesson_title(question) == "Why " + "very " * 22 + "very…"
    assert len(lesson_title(question)) <= 120
    assert lesson_title("How is Kutch Ajrakh made?") == "How is Kutch Ajrakh made?"


def test_the_golden_pack_keeps_its_own_title_and_craft() -> None:
    pack = golden_pack()
    assert pack.title == first_version().mark.question
    assert pack.craft is not None and pack.craft.slug == "Kutch-Ajrakh"
