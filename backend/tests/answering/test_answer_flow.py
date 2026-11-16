import json
from pathlib import Path

from app.core.errors import ExternalFailure
from app.providers.router import RouterError
from app.research.crafts import CraftResolution
from app.research.retrieval import KnowledgeHits
from app.services import answering
from app.services.answer_events import cited_claims
from app.services.answering import AnswerAsk

from ..composer.fixtures import QUESTION, answer, pack, quote, sentence
from ..research.fixtures import AJRAKH, BAGRU
from .fakes import (
    ALUM_CLAIM_ID,
    GUESS_CLAIM_ID,
    SOURCES,
    VIEWS,
    FakeResearch,
    FakeStore,
    pipeline,
    resolved,
    streamed,
)

REPO = Path(__file__).resolve().parents[3]
LAKE_PAPER = "crossref:10.1000/lake"
WEB_PAGE = "searxng:https://crafts.example.org/ajrakh"
REPLY = answer(
    (
        "Mordant",
        [
            sentence(
                "Alum is the mordant that binds alizarin to cotton.",
                quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
            ),
            sentence(
                "Mordant baths held 8 g/L alum and were heated to 60 °C.",
                quote(LAKE_PAPER, "Mordanting baths of 8 g/L alum were heated to 60 °C"),
            ),
            sentence(
                "Lime in the wash water may brighten the red.",
                quote(GUESS_CLAIM_ID, "Lime in the wash water may brighten the red"),
            ),
        ],
    ),
    (
        "Fastness",
        [sentence("The red lake withstood 20 washes.", quote(WEB_PAGE, "the lake withstood 20 washes"))],
    ),
    follow_ups=["How is the alum bath prepared for Kutch Ajrakh?"],
)


def hybrid(**changes: object) -> AnswerAsk:
    fields: dict[str, object] = {"question": QUESTION, "mode": "HYBRID"}
    fields.update(changes)
    return AnswerAsk(**fields)


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        if block:
            name, data = block.split("\n", 1)
            found.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return found


async def test_a_researched_answer_streams_the_shared_golden_stream() -> None:
    store = FakeStore()
    text = await streamed(hybrid(), pipeline(replies=[REPLY], store=store))
    assert text == (REPO / "shared" / "answer-stream.research.golden.sse").read_text(encoding="utf-8")
    (kept,) = store.kept
    assert kept[0].question == QUESTION


async def test_research_that_finds_nothing_says_what_was_searched() -> None:
    empty = pack(stored=KnowledgeHits(craft_slug=AJRAKH.slug), evidence=(), documents=())
    research = FakeResearch(pack=empty, steps=(("SEARCHING_STORED", 1), ("RESEARCHING", 2)))
    text = await streamed(hybrid(), pipeline(research=research))
    assert text == (REPO / "shared" / "answer-stream.not-enough.golden.sse").read_text(encoding="utf-8")


async def test_deep_questions_plan_deep_and_withhold_the_askers_name() -> None:
    research = FakeResearch()
    await streamed(
        hybrid(mode="DEEP", withheld_terms=("Meera Rao",)), pipeline(research=research, replies=[REPLY])
    )
    (request,) = research.requests
    assert (request.mode, request.craft, request.withheld_terms) == ("DEEP", AJRAKH, ("Meera Rao",))


async def test_verified_answers_come_from_stored_claims_without_research() -> None:
    research = FakeResearch()
    store = FakeStore(stored=cited_claims([VIEWS[0], VIEWS[3]], SOURCES))
    found = events(await streamed(hybrid(mode="VERIFIED"), pipeline(research=research, store=store)))
    assert research.requests == []
    assert [name for name, _ in found] == [
        "status",
        "match",
        "status",
        "source",
        "section",
        "sentence",
        "open_question",
        "follow_ups",
        "done",
    ]
    assert found[2][1] == {"step": "SEARCHING_STORED", "message": "Searching stored findings"}
    assert found[4][1] == {"id": "s1", "heading": "Materials and tools"}
    assert found[5][1]["sentence"]["citations"][0]["claimId"] == str(ALUM_CLAIM_ID)
    assert found[-1] == ("done", {"answerId": None})


async def test_verified_without_stored_claims_is_not_enough_evidence() -> None:
    found = events(await streamed(hybrid(mode="VERIFIED"), pipeline()))
    name, payload = found[-2]
    assert name == "not_enough_evidence"
    assert payload["message"].startswith(
        "There is not enough cited evidence to answer this about Kutch Ajrakh yet."
    )
    assert "No live research ran in VERIFIED mode." in payload["message"]


async def test_an_ambiguous_question_offers_the_candidates_and_stops() -> None:
    first, second = resolved(AJRAKH).candidates[0], resolved(BAGRU).candidates[0]
    ambiguous = CraftResolution(
        status="AMBIGUOUS", craft=None, candidates=[first, second], normalised="print", script="Latn"
    )
    found = events(await streamed(hybrid(), pipeline(resolution=ambiguous)))
    assert found[1:] == [
        ("match", {"status": "AMBIGUOUS", "candidates": [AJRAKH.model_dump(), BAGRU.model_dump()]}),
        ("done", {"answerId": None}),
    ]


async def test_a_question_naming_no_craft_asks_for_one() -> None:
    none = CraftResolution(status="NONE", craft=None, candidates=[], normalised="why", script="Latn")
    found = events(await streamed(hybrid(), pipeline(resolution=none)))
    assert found[1:] == [
        ("match", {"status": "NONE"}),
        ("error", {"message": answering.NO_CRAFT_DETAIL}),
        ("done", {"answerId": None}),
    ]


async def test_an_unknown_slug_is_not_found_without_a_match() -> None:
    none = CraftResolution(status="NONE", craft=None, candidates=[], normalised="why", script="Latn")
    found = events(await streamed(hybrid(craft_slug="No-Such-Craft"), pipeline(resolution=none)))
    assert found[1:] == [("error", {"message": answering.NOT_FOUND_DETAIL}), ("done", {"answerId": None})]


async def test_a_failed_resolution_says_so_without_detail() -> None:
    failure = ExternalFailure("embedding route timed out", kind="unavailable", service="embeddings")
    found = events(await streamed(hybrid(), pipeline(resolution=failure)))
    assert found[1:] == [
        ("error", {"message": answering.RESOLVER_FAILED_DETAIL}),
        ("done", {"answerId": None}),
    ]


async def test_a_spent_allowance_while_finding_the_craft_is_shown_in_its_own_words() -> None:
    allowance = "The daily AI spending ceiling has been reached. Asking resumes at midnight IST."
    failure = RouterError("ceiling", allowance, reason="global_daily_cap")
    found = events(await streamed(hybrid(), pipeline(resolution=failure)))
    assert found[1:] == [("error", {"message": allowance}), ("done", {"answerId": None})]


async def test_a_spent_allowance_is_shown_in_its_own_words() -> None:
    allowance = "You have reached today's AI allowance for your role. It resets at midnight IST."
    research = FakeResearch(failure=RouterError("ceiling", allowance, reason="role_daily_cap"))
    found = events(await streamed(hybrid(), pipeline(research=research)))
    assert found[-2:] == [("error", {"message": allowance}), ("done", {"answerId": None})]


async def test_a_failed_live_research_hides_the_detail() -> None:
    failure = ExternalFailure("every source failed: 503 from api.example", kind="unavailable", service="x")
    found = events(await streamed(hybrid(), pipeline(research=FakeResearch(failure=failure))))
    assert found[-2:] == [
        ("error", {"message": answering.RESEARCH_FAILED_DETAIL}),
        ("done", {"answerId": None}),
    ]


async def test_an_unexpected_failure_still_ends_the_stream() -> None:
    found = events(await streamed(hybrid(), pipeline(research=FakeResearch(failure=RuntimeError("boom")))))
    assert found[-2:] == [("error", {"message": answering.UNEXPECTED_DETAIL}), ("done", {"answerId": None})]


def test_status_messages_count_in_words() -> None:
    assert answering.status_message("RESEARCHING", 1) == "Searching 1 live query"
    assert answering.status_message("READING", 2) == "Reading the best of 2 sources found"
    assert answering.status_message("PLANNING", craft="Bagru Print") == "Planning the research on Bagru Print"
