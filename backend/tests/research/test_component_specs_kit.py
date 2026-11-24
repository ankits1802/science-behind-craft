import copy
import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.mcp_component_schemas import component_schema_text
from app.research.component_specs import checked_spec
from app.research.component_specs_either import EITHER_FORMS
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.research.component_specs_kit import DeclaredDiagramSpec
from app.research.component_specs_science_figures import DiagramSpec

FACT = uuid.UUID("2a26748e-4f03-5009-a9f5-7aac56adc219")
CLOTH = {"part": "cloth", "form": "swatch", "material": "--dye-cloth", "label": "u0005"}
BATH = {
    "part": "bath",
    "vessel": "vat",
    "liquor": "--dye-vat-liquor",
    "piece": "--dye-leuco",
    "label": "u0007",
}
SECTION = {
    "part": "section",
    "layers": [
        {"material": "earth", "label": "u0009"},
        {"material": "--dye-mud", "label": "u0010"},
        {"material": "--dye-cloth", "label": "u0011"},
    ],
    "label": "u0008",
}
SEQUENCE: dict[str, Any] = {
    "head": {"title": "u0001", "caption": "u0002"},
    "layout": "sequence",
    "alt": "u0003",
    "panels": [
        {"label": "u0004", "parts": [CLOTH]},
        {"label": "u0006", "via": "u0012", "motion": "dip", "parts": [BATH]},
    ],
}
SECTION_DIAGRAM: dict[str, Any] = {
    "head": {"title": "u0001"},
    "layout": "section",
    "alt": "u0003",
    "panels": [{"label": "u0004", "parts": [SECTION]}],
}
CHAIN = {
    "chain": {
        "headingId": "chain-t",
        "heading": "u0001",
        "links": [
            {"kicker": "u0002", "parts": [{"part": "text", "text": {"tag": "p", "unit": "u0003"}}]},
            {"kicker": "u0004", "parts": [{"part": "text", "text": {"tag": "p", "unit": "u0005"}}]},
        ],
    }
}


def units(refs: list[str], *, plain: tuple[str, ...] = ()) -> dict[str, DeliveredUnit]:
    return {ref: DeliveredUnit(text=f"Label {ref}", claim_ids=[] if ref in plain else [FACT]) for ref in refs}


def changed(spec: dict[str, Any], change: Any) -> dict[str, Any]:
    edited = copy.deepcopy(spec)
    change(edited)
    return edited


def one_layer(spec: dict[str, Any]) -> None:
    section = spec["panels"][0]["parts"][0]
    section["layers"] = section["layers"][:1]


SEQUENCE_REFS = [f"u{n:04d}" for n in range(1, 13) if n not in (8, 9, 10, 11)]
SECTION_REFS = ["u0001", "u0003", "u0004", "u0008", "u0009", "u0010", "u0011"]


def test_a_diagram_with_a_head_is_composed_from_the_kit_and_one_without_is_authored() -> None:
    assert EITHER_FORMS["diagram"] == {"declared": DeclaredDiagramSpec, "authored": DiagramSpec}
    assert isinstance(checked_spec("diagram", SEQUENCE), DeclaredDiagramSpec)
    assert isinstance(checked_spec("diagram", SECTION_DIAGRAM), DeclaredDiagramSpec)
    assert isinstance(checked_spec("diagram", CHAIN), DiagramSpec)


def test_a_composed_diagram_resting_on_cited_labels_passes_the_delivery_gates() -> None:
    assert spec_problems("diagram", SEQUENCE, units(SEQUENCE_REFS, plain=("u0001", "u0004", "u0006"))) == []
    assert spec_problems("diagram", SECTION_DIAGRAM, units(SECTION_REFS, plain=("u0001", "u0004"))) == []


def test_each_part_s_label_and_each_layer_s_label_rests_on_a_cited_fact() -> None:
    problems = spec_problems("diagram", SECTION_DIAGRAM, units(SECTION_REFS, plain=("u0004", "u0010")))
    assert problems == [
        "the unit u0010, the label of layer 2 of panel 1's section, cites no fact: a kit part's label rests "
        "on the facts that state it"
    ]
    problems = spec_problems("diagram", SEQUENCE, units(SEQUENCE_REFS, plain=("u0005",)))
    assert problems == [
        "the unit u0005, the label of panel 1's cloth part, cites no fact: a kit part's label rests on the "
        "facts that state it"
    ]


@pytest.mark.parametrize(
    ("change", "says"),
    [
        (lambda spec: spec.update(layout="before_after", panels=spec["panels"] * 2), "has 2 panels, not 4"),
        (lambda spec: spec.update(layout="steps", panels=spec["panels"][:1]), "has 2 to 6 panels, not 1"),
        (lambda spec: spec["panels"][0].update(via="u0013"), "on the arrow into a later panel"),
        (lambda spec: spec.update(layout="steps"), "only a sequence or a before and after names a change"),
        (lambda spec: spec["panels"][1]["parts"][0].pop("piece"), "the dip motion explains a bath part"),
        (lambda spec: spec["panels"][0].update(motion="dry"), "a paste part that names what it dries to"),
        (lambda spec: spec["panels"][0]["parts"][0].update(material="--ink-1"), "not a depicted material"),
        (lambda spec: spec["panels"][0]["parts"][0].update(material="--dye-ultramarine"), "not a depicted"),
        (lambda spec: spec["panels"][0]["parts"][0].update(part="loom"), "part"),
        (lambda spec: spec["panels"][0].update(parts=[CLOTH] * 4), "at most 3"),
        (
            lambda spec: spec["panels"][0]["parts"][0].update(
                printed={"motif": "paisley", "material": "--dye-kut"}
            ),
            "motif",
        ),
    ],
)
def test_a_composed_diagram_off_the_kit_is_refused_by_its_model(change: Any, says: str) -> None:
    with pytest.raises(ValidationError, match=says):
        checked_spec("diagram", changed(SEQUENCE, change))


def test_a_section_holds_one_section_part_of_two_to_six_layers_and_earth_by_its_word() -> None:
    with pytest.raises(ValidationError, match="holds one section part and nothing else"):
        checked_spec(
            "diagram", changed(SECTION_DIAGRAM, lambda spec: spec["panels"][0]["parts"].append(CLOTH))
        )
    with pytest.raises(ValidationError, match="at least 2"):
        checked_spec("diagram", changed(SECTION_DIAGRAM, one_layer))
    checked = checked_spec("diagram", SECTION_DIAGRAM).model_dump(mode="json")
    assert [layer["material"] for layer in checked["panels"][0]["parts"][0]["layers"]] == [
        "earth",
        "--dye-mud",
        "--dye-cloth",
    ]


def test_the_stored_spec_keeps_only_what_was_said_and_a_tool_is_held_unless_said_otherwise() -> None:
    tool = {"part": "tool", "tool": "chisel", "label": "u0005"}
    spec = changed(SEQUENCE, lambda edited: edited["panels"][0].update(parts=[tool]))
    dumped = checked_spec("diagram", spec).model_dump(mode="json")
    assert dumped["panels"][0] == {
        "label": "u0004",
        "parts": [{"part": "tool", "tool": "chisel", "held": True, "label": "u0005"}],
    }
    assert "text" not in dumped["panels"][1] and dumped["panels"][1]["via"] == "u0012"


def test_the_published_schema_of_a_diagram_offers_both_forms() -> None:
    schema = json.loads(component_schema_text("diagram"))
    text = json.dumps(schema)
    assert '"layout"' in text and '"panels"' in text and '"chain"' in text
    assert '"before_after"' in text and '"piece"' in text
