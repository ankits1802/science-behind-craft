import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.research import stream
from app.research.blocks_lede import LedeBlock
from app.research.explainer import BlockEvent, Explainer, LedeEvent, explainer_blocks, payload_sentences
from app.research.quotes import QUOTE_OVERLAP_MIN, quote_overlap, unsupported_figures
from app.research.sections import fallback_heading, is_facet_label, question_order
from app.services.stated_names import unstated_names

from ..research.signature_fixtures import SIGNATURE_DECLARED
from .explainer_golden import citations_in, golden_json, seed_citations, seed_claims
from .golden import golden_text, reproduces

DOCUMENT = "explainer.lede.golden.json"
STREAM = "explainer.lede.golden.sse"
UNDERSTOOD_FIELDS = ["PROCESS", "MATERIALS", "CHEMISTRY"]


def document() -> dict[str, Any]:
    return copy.deepcopy(golden_json(DOCUMENT))


def frames() -> list[tuple[str, dict[str, Any]]]:
    found = []
    for block in golden_text(STREAM).split("\n\n"):
        if block:
            name, data = block.split("\n")
            found.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return found


def test_the_lede_golden_and_its_stream_are_reproduced_byte_for_byte() -> None:
    assert reproduces(Explainer, DOCUMENT)
    rebuilt = "".join(stream.event_frame(name, data) for name, data in frames())
    assert rebuilt == golden_text(STREAM)


def test_every_citation_resolves_to_a_seeded_claim_source() -> None:
    seeded = seed_citations()
    for cite in citations_in(golden_json(DOCUMENT)):
        row = seeded[cite["id"]]
        assert (cite["claimId"], cite["sourceId"], cite["quote"], cite["level"]) == (
            row["claimId"],
            row["sourceId"],
            row["quote"],
            row["level"],
        )


def test_the_lede_names_alum_and_myrobalan_and_passes_every_prose_check() -> None:
    lede = Explainer.model_validate(golden_json(DOCUMENT)).lede
    assert lede is not None and lede.headline == golden_json(DOCUMENT)["question"]
    shown = " ".join(sentence.text for sentence in lede.sentences).casefold()
    assert "alum" in shown and "myrobalan" in shown
    claims = seed_claims()
    for sentence in lede.sentences:
        supports = [
            *(claims[c.claim_id]["text"] for c in sentence.citations),
            *(c.quote for c in sentence.citations if c.quote),
        ]
        assert sentence.citations
        assert unsupported_figures(sentence.text, supports) == []
        assert unstated_names(sentence.text, supports) == []
        assert quote_overlap(sentence.text, supports) >= QUOTE_OVERLAP_MIN


def test_sections_follow_the_question_and_no_heading_is_a_field_label() -> None:
    body = Explainer.model_validate(golden_json(DOCUMENT))
    assert [s.discipline for s in body.sections] == question_order(
        UNDERSTOOD_FIELDS, body.question, "Kutch Ajrakh"
    )
    assert body.sections[0].discipline == "CHEMISTRY"
    assert body.sections[-1].discipline == "PROCESS"
    assert not any(is_facet_label(section.title) for section in body.sections)
    assert body.question not in body.follow_ups


def test_the_stream_sends_the_lede_first_and_reduces_to_the_document() -> None:
    found = frames()
    names = [name for name, _ in found]
    assert names.index("lede") < names.index("block")
    body = golden_json(DOCUMENT)
    sections: dict[str, dict[str, Any]] = {}
    sent: list[str] = []
    for name, data in found:
        if name == "section_started":
            assert data["title"] == fallback_heading(data["discipline"], "Kutch Ajrakh")
            sections[data["id"]] = {
                "id": data["id"],
                "discipline": data["discipline"],
                "title": data["title"],
            }
            sections[data["id"]] |= {"order": data["order"], "blocks": []}
        elif name == "section_heading":
            sections[data["sectionId"]]["title"] = data["title"]
        elif name == "block":
            sections[data["sectionId"]]["blocks"].append(data["block"])
        elif name == "section_done":
            sections[data["sectionId"]] |= {"state": data["state"], "searched": data["searched"]}
        elif name == "source":
            sent.append(data["id"])
        elif name == "lede":
            assert {c["sourceId"] for c in citations_in(data["block"])} <= set(sent)
            assert data["block"] == body["lede"]
    assert sorted(sections.values(), key=lambda s: s["order"]) == body["sections"]
    assert sent == [source["id"] for source in body["sources"]]
    assert dict(found)["follow_ups"]["items"] == body["followUps"]


def test_the_lede_is_the_first_block_its_sources_lead_and_its_sentences_translate() -> None:
    body = Explainer.model_validate(golden_json(DOCUMENT))
    assert next(iter(explainer_blocks(body))).kind == "lede"
    assert [s.id for s in body.sources][:1] == body.lede.cited_source_ids()[:1]
    lede = golden_json(DOCUMENT)["lede"]
    assert [s["id"] for s in payload_sentences(lede)] == ["lede.1", "lede.2", "lede.3"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda b: b["lede"].update(headline="Why is Ajrakh red?"), "headline is the question"),
        (lambda b: b["lede"].update(sentences=b["lede"]["sentences"][:1]), "at least 2"),
        (lambda b: b["lede"].update(id="s1.b9"), "lede's id"),
        (
            lambda b: b["lede"].update(reuse={"pieceId": b["answerId"], "storedAt": b["createdAt"]}),
            "never reused",
        ),
        (
            lambda b: b["sections"][0]["blocks"].append(
                {
                    "id": "s1.figure",
                    "kind": "mordant_bath",
                    "version": 1,
                    "reuse": None,
                    **SIGNATURE_DECLARED["mordant_bath"],
                }
            ),
            "not built yet",
        ),
        (lambda b: b["sources"].reverse(), "order of first citation"),
    ],
)
def test_the_lede_rules_fail_closed(change: Any, message: str) -> None:
    body = document()
    change(body)
    with pytest.raises(ValidationError, match=message):
        Explainer.model_validate(body)


def test_a_lede_states_facts_only_and_its_event_carries_a_built_figure() -> None:
    lede = document()["lede"]
    for cite in lede["sentences"][0]["citations"]:
        cite["level"] = "HYPOTHESIS"
    lede["sentences"][0]["level"] = "HYPOTHESIS"
    with pytest.raises(ValidationError, match="a hypothesis is an open question"):
        LedeBlock.model_validate(lede)
    figure = {
        "id": "lede.figure",
        "kind": "firing",
        "version": 1,
        "reuse": None,
        **SIGNATURE_DECLARED["firing"],
    }
    shown = document()["lede"] | {"figure": figure}
    assert LedeBlock.model_validate(shown).figure is not None
    assert LedeEvent.model_validate({"block": shown}).block.figure.kind == "firing"
    with pytest.raises(ValidationError, match="not built yet"):
        BlockEvent.model_validate({"sectionId": "s1", "block": figure})
