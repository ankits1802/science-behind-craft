import json
import uuid

import pytest

from app.composer.candidates import compose_request
from app.composer.composer import ModelComposer
from app.composer.prompt import (
    COMPOSE_SYSTEM_PROMPT,
    REGENERATE_SYSTEM_PROMPT,
    compose_schema,
    regenerate_schema,
)
from app.core.errors import ExternalFailure
from app.research.composition import ComposedSentence, Composer, ComposeRequest, QuotedSpan
from app.research.crafts import craft_block
from app.research.retrieval import KnowledgeHits

from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH
from .fixtures import (
    ALUM_CLAIM_ID,
    GUESS_CLAIM_ID,
    QUESTION,
    answer,
    pack,
    quote,
    replacements,
    sentence,
)

CLAIM = str(ALUM_CLAIM_ID)
GUESS = str(GUESS_CLAIM_ID)
ABSTRACT = "crossref:10.1000/lake"
PAGE = "searxng:https://crafts.example.org/ajrakh"
GOOD = sentence(
    "Alum binds alizarin to cotton in Ajrakh.",
    quote(CLAIM, "Alum is the mordant that binds alizarin to cotton"),
)
GOOD_FIGURES = sentence(
    "Mordant baths held 8 g/L alum and were heated to 60 °C.",
    quote(ABSTRACT, "Mordanting baths of 8 g/L alum were heated to 60 °C"),
)


def request() -> ComposeRequest:
    return compose_request(pack(), QUESTION)


async def compose(*replies: str) -> tuple[object, FakeModel]:
    model = FakeModel(list(replies))
    composer = ModelComposer(model=model)
    assert isinstance(composer, Composer)
    return await composer.compose(request()), model


async def test_cited_sentences_are_kept_and_hypotheses_become_open_questions() -> None:
    hypothesis = sentence(
        "Lime in the wash water may brighten the red.",
        quote(GUESS, "Lime in the wash water may brighten the red"),
    )
    reply = answer(
        ("How alum fixes the red", [GOOD, GOOD_FIGURES, hypothesis]),
        follow_ups=["Which plants give Ajrakh its blue?"],
    )
    result, model = await compose(reply)
    assert len(model.calls) == 1
    [section] = result.sections
    assert section.heading == "How alum fixes the red"
    assert section.sentences == [
        ComposedSentence(
            text="Alum binds alizarin to cotton in Ajrakh.",
            claimIds=[ALUM_CLAIM_ID],
            spans=[QuotedSpan(ref=CLAIM, text="Alum is the mordant that binds alizarin to cotton")],
        ),
        ComposedSentence(
            text="Mordant baths held 8 g/L alum and were heated to 60 °C.",
            evidenceIds=[ABSTRACT],
            spans=[QuotedSpan(ref=ABSTRACT, text="Mordanting baths of 8 g/L alum were heated to 60 °C")],
        ),
    ]
    assert [s.claim_ids for s in result.open_questions] == [[GUESS_CLAIM_ID]]
    assert result.follow_ups == ["Which plants give Ajrakh its blue?"]
    assert result.not_enough_evidence is None


async def test_the_model_sees_every_passage_as_data_and_answers_to_the_schema() -> None:
    _, model = await compose(answer(("Alum", [GOOD])))
    [call] = model.calls
    assert call["system"] == COMPOSE_SYSTEM_PROMPT
    assert call["schema"] == compose_schema()
    user = call["user"]
    assert user.startswith(f"Answer language: en\n{craft_block(AJRAKH)}\n")
    assert f'<untrusted_source ref="{CLAIM}" label="stored claim, reviewed; passage 1 of 1">' in user
    assert (
        f'<untrusted_source ref="{PAGE}" label="Ajrakh fastness notes (searxng, undated, full text);' in user
    )
    assert "passage 2 of 2" in user
    assert user.endswith(
        f'<untrusted_source ref="question" label="learner question">\n{QUESTION}\n</untrusted_source>'
    )
    assert user.count("<untrusted_source ") == user.count("</untrusted_source>") == 7
    assert "Alizarin forms an insoluble red lake" not in call["system"]


async def test_failing_sentences_are_regenerated_once_and_dropped_if_still_failing() -> None:
    first = answer(
        (
            "Alum",
            [
                GOOD,
                sentence("Baths were heated to 70 °C.", quote(ABSTRACT, "were heated to 60 °C")),
                sentence("Alum is toxic.", quote(ABSTRACT, "alum is toxic to the dyers")),
                sentence("Ajrakh is old."),
            ],
        )
    )
    second = replacements(
        (0, sentence("Baths were heated to 60 °C.", quote(ABSTRACT, "were heated to 60 °C"))),
        (1, sentence("Alum is toxic at 5 ppm.", quote(ABSTRACT, "Alizarin forms an insoluble red lake"))),
    )
    result, model = await compose(first, second)
    assert [s.text for s in result.sections[0].sentences] == [
        "Alum binds alizarin to cotton in Ajrakh.",
        "Baths were heated to 60 °C.",
    ]
    retry = model.calls[1]
    assert retry["system"] == REGENERATE_SYSTEM_PROMPT
    assert retry["schema"] == regenerate_schema(3)
    assert "Failed sentence 0: UNSUPPORTED_FIGURE\n" in retry["user"]
    assert "Failed sentence 1: SPAN_NOT_IN_SOURCE\n" in retry["user"]
    assert "Failed sentence 2: UNCITED\n" in retry["user"]
    assert "(section " not in retry["user"]
    assert (
        '<untrusted_source ref="failed-1" label="earlier model output">\nSection: Alum\n'
        f"Problems: SPAN_NOT_IN_SOURCE: {ABSTRACT}\nSentence: Alum is toxic.\n</untrusted_source>"
    ) in retry["user"]


async def test_a_malformed_sentence_is_regenerated_not_fatal() -> None:
    too_long = sentence("Alum binds alizarin.", quote(CLAIM, "x" * 301))
    result, model = await compose(answer(("Alum", [too_long])), replacements((0, GOOD)))
    assert "Failed sentence 0: MALFORMED\n" in model.calls[1]["user"]
    assert "Problems: MALFORMED: text\nSentence: Alum binds alizarin.\n" in model.calls[1]["user"]
    assert [s.text for s in result.sections[0].sentences] == ["Alum binds alizarin to cotton in Ajrakh."]


async def test_an_unusable_reply_is_asked_again_once_and_then_raised() -> None:
    late_failure = sentence("Heated to 99 °C.", quote(ABSTRACT, "heated to 60 °C"))
    result, model = await compose("not json", answer(("Alum", [GOOD, late_failure])))
    assert len(model.calls) == 2
    assert [s.text for s in result.sections[0].sentences] == ["Alum binds alizarin to cotton in Ajrakh."]
    with pytest.raises(ExternalFailure, match="compose reply is unusable: sections is missing"):
        await compose(json.dumps({"followUps": []}), json.dumps({"sections": "none", "followUps": []}))


async def test_an_unusable_regenerate_reply_drops_the_failing_sentences() -> None:
    first = answer(("Alum", [GOOD, sentence("Heated to 99 °C.", quote(ABSTRACT, "heated to 60 °C"))]))
    result, model = await compose(first, "[]")
    assert len(model.calls) == 2
    assert [s.text for s in result.sections[0].sentences] == ["Alum binds alizarin to cotton in Ajrakh."]


async def test_when_nothing_survives_the_answer_says_what_was_searched() -> None:
    first = answer(("Alum", [sentence("Alum dates to 2500 BCE.", quote(CLAIM, "Alum is the mordant"))]))
    result, model = await compose(first, replacements())
    assert len(model.calls) == 2
    assert (result.sections, result.open_questions, result.follow_ups) == ([], [], [])
    assert result.not_enough_evidence == request().searched


async def test_no_candidates_means_no_model_call() -> None:
    empty = compose_request(
        pack(stored=KnowledgeHits(craft_slug=AJRAKH.slug), evidence=(), documents=(), failures=()), QUESTION
    )
    model = FakeModel([])
    result = await ModelComposer(model=model).compose(empty)
    assert model.calls == []
    assert result.not_enough_evidence == empty.searched


async def test_an_unknown_id_is_never_trusted_even_if_quoted_right() -> None:
    forged = str(uuid.UUID(int=1))
    first = answer(("Alum", [sentence("Alum is the mordant.", quote(forged, "Alum is the mordant"))]))
    result, _ = await compose(first, replacements())
    assert result.not_enough_evidence is not None
