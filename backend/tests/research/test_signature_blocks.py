import copy
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.research.blocks_signature import SIGNATURE_KINDS, SIGNATURE_TERMS, SignatureBlock, chosen_signature
from app.research.explainer import BLOCK_MODELS, BUILT_BLOCK_KINDS, payload_sentences

from .signature_fixtures import SIGNATURE_DECLARED, cited

FIGURE = TypeAdapter(SignatureBlock)


def figure(kind: str) -> dict[str, Any]:
    return {
        "id": "s1.b9",
        "kind": kind,
        "version": 1,
        "reuse": None,
        **copy.deepcopy(SIGNATURE_DECLARED[kind]),
    }


def test_the_signature_kinds_are_declared_with_their_shapes_and_not_built_yet() -> None:
    assert set(SIGNATURE_KINDS) <= set(BLOCK_MODELS)
    assert not set(SIGNATURE_KINDS) & set(BUILT_BLOCK_KINDS)
    assert set(SIGNATURE_TERMS) == set(SIGNATURE_KINDS)
    for kind in SIGNATURE_KINDS:
        assert type(FIGURE.validate_python(figure(kind))) is BLOCK_MODELS[kind]


@pytest.mark.parametrize(
    ("terms", "expected"),
    [
        (["indigo", "alum"], "indigo_vat"),
        (["red", "alum"], "mordant_bath"),
        (["dhokra"], "lost_wax"),
        (["terracotta"], "firing"),
        (["madder", "indigo"], "mordant_bath"),
        (["cotton"], None),
        ([], None),
    ],
)
def test_the_figure_follows_the_first_concept_of_the_answer_that_has_one(
    terms: list[str], expected: str | None
) -> None:
    assert chosen_signature(terms) == expected


def test_every_figure_sentence_is_walked_for_translation_and_terms() -> None:
    vat = figure("indigo_vat")
    assert [s["id"] for s in payload_sentences(vat)] == ["v.1", "v.2", "v.3", "v.4", "v.5"]
    assert [s["id"] for s in payload_sentences(figure("firing"))] == ["f.1", "f.2", "f.3"]


def broken_dips(block: dict[str, Any]) -> None:
    block["dips"][0]["dips"] = 5


def unstated_colour(block: dict[str, Any]) -> None:
    block["swatches"][1]["colour"] = "crimson"


def twice_alum(block: dict[str, Any]) -> None:
    block["swatches"][2]["mordant"] = "alum"
    block["swatches"][2]["sentence"] = cited("m.3", "With alum the madder bath turns the cloth black.")


def steps_out_of_order(block: dict[str, Any]) -> None:
    block["steps"].reverse()


def unnamed_metal(block: dict[str, Any]) -> None:
    block["metal"] = "bell metal"


def two_oxidising(block: dict[str, Any]) -> None:
    block["atmospheres"][1]["atmosphere"] = "OXIDISING"


def hypothesis_lift(block: dict[str, Any]) -> None:
    block["lift"] = cited("v.1", "At first bright green, the cloth may become blue.", level="HYPOTHESIS")


@pytest.mark.parametrize(
    ("kind", "change", "message"),
    [
        ("indigo_vat", broken_dips, "does not state 5 dips"),
        ("indigo_vat", hypothesis_lift, "a hypothesis is an open question"),
        ("mordant_bath", unstated_colour, "which its sentence does not state"),
        ("mordant_bath", twice_alum, "each mordant, or no mordant, once"),
        ("lost_wax", steps_out_of_order, "in casting order"),
        ("lost_wax", unnamed_metal, "which no step sentence states"),
        ("firing", two_oxidising, "each atmosphere once"),
    ],
)
def test_a_figure_shows_only_what_its_cited_sentences_state(kind: str, change: Any, message: str) -> None:
    block = figure(kind)
    change(block)
    with pytest.raises(ValidationError, match=message):
        FIGURE.validate_python(block)
