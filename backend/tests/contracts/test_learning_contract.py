import copy
from collections import Counter
from typing import Any

import pytest
from pydantic import ValidationError

from app.research import stream
from app.research.alerts import Notification, SavedExplainer
from app.research.explainer import Explainer
from app.research.explainer_versions import VersionMark, version_problems
from app.research.lessons import LessonPack, LessonRequest

from .explainer_golden import DOCUMENT, citations_in, golden_json, seed_citations, seed_claims
from .golden import reproduces
from .learning_golden import ALERTS, LESSON, VERSIONS, AlertsFixture, LessonFixture, VersionsFixture, learning


def versions() -> VersionsFixture:
    return VersionsFixture.model_validate(learning(VERSIONS))


def first() -> Explainer:
    return Explainer.model_validate(golden_json(DOCUMENT))


def latest_payload() -> dict[str, Any]:
    return copy.deepcopy(learning(VERSIONS)["latest"]["explainer"])


def with_sources_as_cited(payload: dict[str, Any]) -> Explainer:
    known = {source["id"]: source for source in payload["sources"]}
    ordered = dict.fromkeys(c["sourceId"] for c in citations_in(payload["sections"]))
    return Explainer.model_validate(payload | {"sources": [known[sid] for sid in ordered]})


def changes() -> list[Any]:
    return list(versions().latest.mark.changes)


@pytest.mark.parametrize(
    ("fixture", "name"), [(VersionsFixture, VERSIONS), (AlertsFixture, ALERTS), (LessonFixture, LESSON)]
)
def test_the_learning_fixtures_are_reproduced_byte_for_byte(fixture: Any, name: str) -> None:
    assert reproduces(fixture, name)


def test_a_follow_up_deepens_the_water_section_and_adds_a_history_section() -> None:
    body = versions()
    assert [(c.section_id, c.change, c.block_ids) for c in body.latest.mark.changes] == [
        ("s2", "DEEPENED", ["s2.b2"]),
        ("s4", "ADDED", ["s4.b1"]),
    ]
    assert version_problems(first(), body.latest.explainer, body.latest.mark.changes) == []
    assert [mark.version for mark in body.history.versions] == [1, 2]
    assert body.history.versions[1] == body.latest.mark
    assert str(body.history.versions[0].answer_id) == golden_json(DOCUMENT)["answerId"]


def test_every_sentence_a_follow_up_adds_is_a_seeded_claim_with_resolving_citations() -> None:
    explainer = versions().latest.explainer
    added = [b for s in explainer.sections for b in s.blocks if b.id in {"s2.b2", "s4.b1"}]
    seeded = seed_citations()
    for block in added:
        for sentence in block.cited_sentences():
            claim = seed_claims()[sentence.citations[0].claim_id]
            assert (sentence.text, sentence.level) == (claim["text"], claim["evidenceLevel"])
            for citation in sentence.citations:
                assert seeded[citation.id]["quote"] == citation.quote


def test_an_older_version_keeps_every_citation_it_showed() -> None:
    older = {c["id"] for c in citations_in(golden_json(DOCUMENT)["sections"])}
    newer = {c["id"] for c in citations_in(learning(VERSIONS)["latest"]["explainer"]["sections"])}
    assert older < newer


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda e: e["sections"][1]["blocks"].pop(0), "keeps every block it showed"),
        (lambda e: e["sections"][0].update(title="Making"), "keeps its field, title and place"),
        (lambda e: e["sections"][1]["blocks"].reverse(), "adds after them"),
        (lambda e: e["understood"].update(depth="BASIC"), "keeps the explainer's crafts"),
    ],
)
def test_a_follow_up_never_rewrites_what_an_older_version_showed(change: Any, message: str) -> None:
    payload = latest_payload()
    change(payload)
    problems = version_problems(first(), with_sources_as_cited(payload), changes())
    assert any(message in problem for problem in problems)


def test_the_changes_name_exactly_what_was_added() -> None:
    latest = versions().latest.explainer
    assert any("changes name every added" in p for p in version_problems(first(), latest, changes()[:1]))
    assert any("adds or deepens" in p for p in version_problems(first(), first(), []))


def test_version_marks_chain_from_the_first_answer() -> None:
    mark = versions().history.versions[1].model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="builds on version 1 and changes it"):
        VersionMark.model_validate(mark | {"changes": []})
    with pytest.raises(ValidationError, match="based on nothing"):
        VersionMark.model_validate(mark | {"version": 1, "basedOn": None})


def test_the_version_events_reach_the_wire() -> None:
    body = versions()
    frame = stream.event_frame("version", body.latest.mark)
    assert frame.startswith("event: version\n") and '"basedOn":1' in frame
    builds_on = stream.event_frame("builds_on", body.builds_on)
    assert '"sections":[{"id":"s1","order":1}' in builds_on
    assert [s.id for s in body.builds_on.sections] == [s.id for s in first().sections]


def test_a_saved_explainer_follows_its_latest_version() -> None:
    alerts = AlertsFixture.model_validate(learning(ALERTS))
    saved = alerts.saved.items[0]
    latest = versions().latest
    assert (saved.explainer_id, saved.latest_version) == (latest.mark.explainer_id, latest.mark.version)
    assert saved.facets == [section.discipline for section in latest.explainer.sections]
    assert saved.question == first().question
    payload = saved.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="was seen at a version it has"):
        SavedExplainer.model_validate(payload | {"seenVersion": 3})


def test_an_answer_got_better_note_names_new_findings_in_saved_facets() -> None:
    alerts = AlertsFixture.model_validate(learning(ALERTS))
    note = alerts.notifications.items[0]
    assert note.kind == "ANSWER_IMPROVED" and alerts.notifications.unread == 1
    assert {entry.facet for entry in note.payload.news} <= set(alerts.saved.items[0].facets)
    assert alerts.digest.items == [note.payload]
    assert alerts.digest.week_of.isoformat() == "2026-11-23"
    payload = note.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="read after it was made"):
        Notification.model_validate(payload | {"readAt": "2026-11-18T00:00:00Z"})


def lesson() -> LessonFixture:
    return LessonFixture.model_validate(learning(LESSON))


def test_a_lesson_shows_the_explainer_s_own_sentences_and_picture() -> None:
    pack = lesson().pack
    sentences = {
        s.id: s for b in (x for sec in first().sections for x in sec.blocks) for s in b.cited_sentences()
    }
    bullets = [b for slide in pack.slides for b in slide.bullets]
    assert [b.id for b in bullets] == [
        *(f"s1.b1.{n}" for n in range(1, 7)),
        "s2.b1.1",
        "s2.b1.2",
        "s2.b1.3",
    ] + [f"s3.b1.{n}" for n in range(1, 4)]
    assert all(b == sentences[b.id] for b in bullets)
    picture = golden_json(DOCUMENT)["sections"][0]["blocks"][1]["items"][0]["media"]
    assert pack.slides[1].image is not None and str(pack.slides[1].image.id) == picture["id"]
    assert [s.kind for s in pack.slides] == ["TITLE", *["SECTION"] * 4, *["QUIZ"] * 9, "READING", "SOURCES"]


def test_the_lesson_quiz_blanks_explainer_sentences() -> None:
    quiz = lesson().pack.quiz
    assert quiz is not None
    asked = golden_json("learning.quiz.golden.json")["quiz"]["questions"]
    assert [q.prompt for q in quiz.questions] == [question["prompt"] for question in asked]
    assert [q.answer for q in quiz.questions] == [question["answer"] for question in asked]
    texts = {s.text for sec in first().sections for b in sec.blocks for s in b.cited_sentences()}
    assert all(o.sentence.text in texts for q in quiz.questions for o in q.options)


def test_the_reading_list_runs_by_reliability_then_by_citations() -> None:
    pack = lesson().pack
    shown = [b for slide in pack.slides for b in slide.bullets] + list(pack.quiz.cited_sentences())
    counts = Counter(sid for s in shown for sid in {c.source_id for c in s.citations})
    reading = [(item.source.reliability, item.cited_by) for item in pack.reading_list]
    assert reading == [("A", 40), ("A", 1), ("A", 1), ("B", 6), ("B", 1)]
    assert all(counts[item.source.id] == item.cited_by for item in pack.reading_list)


def test_a_lesson_keeps_its_slide_order_and_shows_only_open_pictures() -> None:
    payload = copy.deepcopy(learning(LESSON)["pack"])
    payload["slides"][-2]["kind"], payload["slides"][-1]["kind"] = "SOURCES", "READING"
    with pytest.raises(ValidationError, match="title, sections, one slide per quiz question"):
        LessonPack.model_validate(payload)
    payload = copy.deepcopy(learning(LESSON)["pack"])
    payload["slides"][1]["image"]["display"] = "LINK_CARD"
    with pytest.raises(ValidationError, match="openly licensed picture"):
        LessonPack.model_validate(payload)
    request = learning(LESSON)["request"]
    with pytest.raises(ValidationError, match="each section once"):
        LessonRequest.model_validate(request | {"sectionIds": ["s1", "s1"]})
    assert lesson().list.items[0].slide_count == len(lesson().pack.slides)
