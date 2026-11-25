import dataclasses
import hashlib
import logging
import re
from typing import Any

import pytest

from app.composer.simulation import REDRAFT_SYSTEM_PROMPT, SIMULATION_SYSTEM_PROMPT
from app.core.errors import ExternalFailure
from app.research.blocks_play import SimulationBlock
from app.research.sandbox import SANDBOX_MAX_BYTES
from app.research.simulation_draft import SIMULATION_HTML_MAX_CHARS
from app.research.structured import schema_problems
from app.research.untrusted import untrusted_block
from app.services.knowledge_view import ClaimView

from ..contracts.phase_c_golden import corpus
from .fixtures import (
    BUILT_AT,
    CONCEPT,
    HIGH_LABEL,
    LOW_LABEL,
    OPUS,
    QUESTION,
    TITLE,
    WATER_CLAIM,
    WATER_STATED,
    WATER_TEXT,
    DraftModel,
    StoredPieces,
    accepted_html,
    build_ask,
    builder,
    cited,
    draft,
    stored_simulation,
    water_citation,
    water_view,
)

RULES_FAILED = re.compile(r"rules failed: ([A-Z,]+);")


async def built(model: DraftModel, stored: StoredPieces | None = None, **ask: Any) -> list[Any]:
    return list((await builder(model, stored).build(build_ask(**ask))).blocks)


def refused_cases() -> list[dict[str, Any]]:
    return corpus()["refused"]


def logged_rules(caplog: pytest.LogCaptureFixture) -> set[str]:
    found = [RULES_FAILED.search(record.getMessage()) for record in caplog.records]
    return {rule for match in found if match for rule in match.group(1).split(",")}


async def test_a_mechanism_section_gets_an_explainer_fed_only_its_cited_figures() -> None:
    model = DraftModel([draft(accepted_html())])
    (block,) = await built(model)
    citation = water_citation()
    assert isinstance(block, SimulationBlock)
    assert (block.id, block.concept, block.title, block.model, block.created_at) == (
        "s1.simulation",
        CONCEPT,
        TITLE,
        OPUS,
        BUILT_AT,
    )
    assert [(v.key, v.label, v.value, v.unit, v.stated) for v in block.values] == [
        ("fallLowFeet", LOW_LABEL, 10.0, "feet", WATER_STATED),
        ("fallHighFeet", HIGH_LABEL, 15.0, "feet", WATER_STATED),
    ]
    assert {c.id for v in block.values for c in v.citations} == {citation["id"]}
    assert block.html_sha256 == hashlib.sha256(accepted_html().encode("utf-8")).hexdigest()
    assert (block.reuse, block.hidden, block.datasets) == (None, False, [])


async def test_the_one_call_keeps_every_untrusted_text_inside_untrusted_blocks() -> None:
    model = DraftModel([draft(accepted_html())])
    await built(model)
    (call,) = model.calls
    assert call["system"] == SIMULATION_SYSTEM_PROMPT
    assert schema_problems(call["schema"]) == []
    assert untrusted_block("question", "question", QUESTION) in call["user"]
    assert untrusted_block("s1", "statement", WATER_TEXT) in call["user"]
    assert untrusted_block("v1", "value", f"10, stated as: {WATER_STATED}") in call["user"]
    assert untrusted_block("v2", "value", f"15, stated as: {WATER_STATED}") in call["user"]
    assert "Blocks the section already shows: prose" in call["user"]


@pytest.mark.parametrize("case", refused_cases(), ids=lambda case: case["name"])
async def test_every_escape_attempt_is_refused_for_its_own_rule(
    case: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    model = DraftModel([draft(case["html"])])
    with caplog.at_level(logging.INFO):
        assert await built(model) == []
    assert logged_rules(caplog) == {case["rule"]}
    assert len(model.calls) == 2
    assert model.calls[1]["system"] == REDRAFT_SYSTEM_PROMPT
    assert f"{case['rule']}: " in model.calls[1]["user"]


DRAWN_AT_THE_BAR = frozenset({"data figures shown", "button moving a marker"})
SHOWN_AS_AN_IMAGE = "inline data image"


@pytest.mark.parametrize("case", corpus()["accepted"], ids=lambda case: case["name"])
async def test_markup_the_sandbox_accepts_is_kept_at_the_first_draft_only_when_drawn_at_the_bar(
    case: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    model = DraftModel([draft(case["html"])])
    with caplog.at_level(logging.INFO):
        blocks = await built(model)
    if case["name"] in DRAWN_AT_THE_BAR:
        assert [block.html for block in blocks] == [case["html"].strip()]
        assert len(model.calls) == 1
    else:
        assert blocks == [] and len(model.calls) == 2
        assert logged_rules(caplog) == {"ART"}


def test_the_corpus_holds_six_explainers_below_the_bar_and_a_data_image_is_one() -> None:
    names = [case["name"] for case in corpus()["accepted"]]
    assert len(names) == 8 and set(names) >= DRAWN_AT_THE_BAR
    assert SHOWN_AS_AN_IMAGE in names and SHOWN_AS_AN_IMAGE not in DRAWN_AT_THE_BAR


@pytest.mark.parametrize(
    ("html", "kept"),
    [
        ("<script>const fall = 15;</script>", True),
        ("<script>const fall = 17;</script>", False),
        ("<p>The water falls 15 feet.</p>", True),
        ("<p>The water falls 17 feet.</p>", False),
        ("<input type=range min=0 max=17>", False),
    ],
)
async def test_a_numeral_absent_from_the_data_object_is_refused(
    html: str, kept: bool, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        blocks = await built(DraftModel([draft(html)]))
    assert len(blocks) == int(kept)
    assert logged_rules(caplog) == (set() if kept else {"NUMBER"})


async def test_a_draft_past_the_prompt_s_length_is_refused_for_size_and_the_redraft_is_told(
    caplog: pytest.LogCaptureFixture,
) -> None:
    head = accepted_html()
    exact = head + "x" * (SIMULATION_HTML_MAX_CHARS - len(head))
    assert len(exact) == SIMULATION_HTML_MAX_CHARS == 40000
    assert len(await built(DraftModel([draft(exact)]))) == 1
    model = DraftModel([draft(exact + "x")])
    with caplog.at_level(logging.INFO):
        assert await built(model) == []
    assert logged_rules(caplog) == {"SIZE"}
    assert "SIZE: 40001 characters, more than 40000" in model.calls[1]["user"]


async def test_a_reply_past_the_block_s_byte_cap_is_off_its_schema() -> None:
    with pytest.raises(ExternalFailure, match="off its schema"):
        await built(DraftModel([draft("x" * (SANDBOX_MAX_BYTES + 1))]))


async def test_a_redraft_that_passes_is_kept() -> None:
    fetching = accepted_html().replace("draw();\n</script>", 'fetch("#");\ndraw();\n</script>')
    model = DraftModel([draft(fetching), draft(accepted_html())])
    (block,) = await built(model)
    assert block.html == accepted_html().strip()
    assert "API: fetch" in model.calls[1]["user"]
    assert untrusted_block("v1", "value", f"10, stated as: {WATER_STATED}") in model.calls[1]["user"]


async def test_a_section_the_model_finds_no_mechanism_in_adds_nothing() -> None:
    model = DraftModel([draft("", build=False, concept="", title="", values=[])])
    assert await built(model) == []
    assert len(model.calls) == 1


async def test_a_section_whose_quotes_state_no_figure_asks_no_model() -> None:
    plain = water_citation() | {"quote": "Water is the lifeline of printing and dyeing."}
    view = ClaimView(WATER_CLAIM, WATER_TEXT, "PROVISIONAL", "CONCEPT", None, citations=[plain])
    model = DraftModel([draft(accepted_html())])
    assert await built(model, views=[view]) == []
    assert model.calls == []


async def test_a_hypothesis_offers_no_value() -> None:
    model = DraftModel([draft(accepted_html())])
    guessed = dataclasses.replace(build_ask(), cited=cited([water_view(level="HYPOTHESIS")]))
    assert (await builder(model).build(guessed)).blocks == ()
    assert model.calls == []


async def test_a_stored_explainer_whose_claims_the_section_offers_is_reused_with_no_model_call() -> None:
    piece = stored_simulation()
    model, stored = DraftModel([draft(accepted_html())]), StoredPieces([piece])
    (block,) = await built(model, stored, depth="BASIC")
    assert model.calls == []
    assert block.reuse is not None
    assert (block.reuse.piece_id, block.reuse.stored_at) == (piece.id, piece.created_at)
    assert block.model_copy(update={"id": piece.payload.id, "reuse": None}) == piece.payload
    ((claims, facet),) = stored.asked
    assert (claims, facet) == (frozenset(piece.claim_ids), "GEOGRAPHY")


@pytest.mark.parametrize(
    "change",
    [{"depth": "BASIC"}, {"facet": "CHEMISTRY"}, {"hidden_at": BUILT_AT}],
    ids=["shallower", "another field", "hidden"],
)
async def test_a_stored_explainer_that_fails_the_reuse_rule_is_built_again(change: dict[str, Any]) -> None:
    depth = change.pop("depth", "EXPERT")
    facet = change.pop("facet", "GEOGRAPHY")
    piece = stored_simulation(depth=depth, facet=facet, **change)
    model = DraftModel([draft(accepted_html(), concept="Water table falling year by year")])
    (block,) = await built(model, StoredPieces([piece]))
    assert block.reuse is None
    assert len(model.calls) == 1


@pytest.mark.parametrize("facet", ["GEOGRAPHY", "CHEMISTRY"])
async def test_a_hidden_explainer_is_never_built_again_for_its_concept_and_claims(
    facet: str, caplog: pytest.LogCaptureFixture
) -> None:
    hidden = stored_simulation(hidden_at=BUILT_AT, facet=facet)
    model = DraftModel([draft(accepted_html())])
    with caplog.at_level(logging.WARNING):
        assert await built(model, StoredPieces([hidden])) == []
    assert untrusted_block("h1", "hidden concept", CONCEPT) in model.calls[0]["user"]
    assert any(record.getMessage().endswith("adds nothing: HIDDEN") for record in caplog.records)


async def test_a_route_that_names_no_model_fails_the_build() -> None:
    with pytest.raises(ExternalFailure, match="named no model"):
        await built(DraftModel([draft(accepted_html())], model=None))
