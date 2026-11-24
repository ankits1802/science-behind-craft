from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models import enums
from app.research.blocks_kit import KitFigureBlock
from app.research.explainer import BLOCK_PHASES, BUILT_BLOCK_KINDS, Block, BlockEvent
from app.research.knowledge_pieces import UNSTORED_BLOCK_KINDS

from ..contracts.blocks_golden import KIT_FIGURE, BlocksFixture
from ..contracts.golden import golden_json
from ..simulations.fixtures import water_citation

BLOCKS: TypeAdapter[Any] = TypeAdapter(Block)


def label(ref: str, text: str, *, cited: bool = False) -> dict[str, Any]:
    return {"ref": ref, "text": text, **({"citations": [water_citation()]} if cited else {})}


def wire(**changes: Any) -> dict[str, Any]:
    diagram = {
        "head": {"title": "u0001"},
        "layout": "before_after",
        "alt": "u0002",
        "panels": [
            {
                "label": "u0003",
                "parts": [{"part": "cloth", "form": "length", "material": "--dye-leuco", "label": "u0004"}],
            },
            {
                "label": "u0005",
                "motion": "take",
                "parts": [{"part": "cloth", "form": "length", "material": "--dye-indigo", "label": "u0006"}],
            },
        ],
    }
    labels = [
        label("u0001", "Green to blue"),
        label("u0002", "Cloth drawn green, then blue"),
        label("u0003", "Green"),
        label("u0004", "Cloth, green", cited=True),
        label("u0005", "Blue"),
        label("u0006", "Cloth, blue", cited=True),
    ]
    block = {
        "id": "s1.kit",
        "kind": "kit_figure",
        "version": 1,
        "reuse": None,
        "diagram": diagram,
        "labels": labels,
    }
    return block | changes


def test_a_kit_figure_is_a_later_phase_answer_block_drawn_by_the_site_and_never_kept_as_a_piece() -> None:
    block = BLOCKS.validate_python(wire())
    assert isinstance(block, KitFigureBlock)
    assert BlockEvent(section_id="s1", block=block).block == block
    assert BLOCK_PHASES["kit_figure"] == "C"
    assert BUILT_BLOCK_KINDS[-2:] == ("kit_figure", "component")
    assert enums.BLOCK_KINDS[-2:] == ("kit_figure", "component")
    assert "kit_figure" in UNSTORED_BLOCK_KINDS


def test_a_kit_figure_cites_its_parts_and_shows_its_labels() -> None:
    block = BLOCKS.validate_python(wire())
    assert [c.id for c in block.citations()] == [water_citation()["id"]] * 2
    assert block.cited_source_ids() == [water_citation()["sourceId"]]
    assert block.shown_labels() == [
        "Green to blue",
        "Cloth drawn green, then blue",
        "Green",
        "Cloth, green",
        "Blue",
        "Cloth, blue",
    ]
    assert list(block.cited_sentences()) == []


def test_a_kit_figure_round_trips_its_wire_form() -> None:
    block = BLOCKS.validate_python(wire())
    assert BLOCKS.validate_python(block.model_dump(mode="json", by_alias=True)) == block


def uncited_part() -> dict[str, Any]:
    payload = wire()
    payload["labels"][3] = label("u0004", "Cloth, green")
    return payload


def unlabelled() -> dict[str, Any]:
    payload = wire()
    payload["labels"] = payload["labels"][:-1]
    return payload


def label_not_drawn() -> dict[str, Any]:
    payload = wire()
    payload["labels"].append(label("u0007", "Nowhere"))
    return payload


def named_twice() -> dict[str, Any]:
    payload = wire()
    payload["labels"].append(label("u0006", "Cloth, blue", cited=True))
    return payload


@pytest.mark.parametrize(
    ("payload", "said"),
    [
        (uncited_part(), "cites no fact"),
        (unlabelled(), "names exactly the labels its diagram draws"),
        (label_not_drawn(), "names exactly the labels its diagram draws"),
        (named_twice(), "names each label once"),
        (wire(labels=[]), "at least 1 item"),
    ],
)
def test_a_kit_figure_that_breaks_a_rule_is_refused(payload: dict[str, Any], said: str) -> None:
    with pytest.raises(ValidationError, match=said):
        BLOCKS.validate_python(payload)


def test_a_kit_figure_takes_only_the_kit_s_vocabulary() -> None:
    payload = wire()
    payload["diagram"]["panels"][0]["parts"][0]["material"] = "--ink-1"
    with pytest.raises(ValidationError, match="not a depicted material"):
        BLOCKS.validate_python(payload)
    payload = wire()
    payload["diagram"]["panels"][0]["motion"] = "dip"
    with pytest.raises(ValidationError, match="dip motion explains a bath part"):
        BLOCKS.validate_python(payload)


def test_the_shared_kit_figures_read_back_byte_for_byte_and_draw_every_part_of_the_kit() -> None:
    golden = golden_json(KIT_FIGURE)
    fixture = BlocksFixture.model_validate(golden)
    assert fixture.model_dump(mode="json", by_alias=True) == golden
    blocks = fixture.sections[0].blocks
    assert [block.kind for block in blocks] == ["kit_figure"] * 3
    drawn = {part.part for block in blocks for panel in block.diagram.panels for part in panel.parts}
    assert drawn == {"bath", "cloth", "paste", "block", "tool", "heat", "water", "piece", "section"}
    assert [block.diagram.layout for block in blocks] == ["before_after", "steps", "section"]
    assert {source.id for source in fixture.sources} == {
        sid for block in blocks for sid in block.cited_source_ids()
    }
