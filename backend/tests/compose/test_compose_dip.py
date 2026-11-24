import dataclasses
from typing import Any

from app.services.compose_dip import dip_player
from app.services.compose_held import About, HeldAfter, HeldStage

from .held import BAGRU, FACTS, cited_claims, claim, delivery_problems, held, unrecorded

WASHING_IN_WORDS = (
    "a specimen colour for white after the stage S05 (Washing): no depicted material shows it from the "
    "materials it names, so its phase is drawn as an outline and the colour named in words; ask the team for "
    "a specimen record with the source that states it"
)
RINSING_NO_COLOUR = (
    "the colours after the stage S07 (Rinsing): its after names none, so the dip leaves it out; propose "
    "STAGE_AFTER for Bagru-Print again with the colours its fact states, and the stage's dyes, mordants and "
    "resists named by their substance"
)
RINSING = HeldStage("S07", "Rinsing", "WASH", (claim(7),), ("M07",), HeldAfter("Rinsed", (), claim(7)))


def _fills(spec: dict[str, Any]) -> list[str]:
    return [phase["drawing"]["children"][1]["attrs"]["fill"] for phase in spec["phases"]]


def test_a_dip_player_plays_the_craft_s_bath_stages_in_the_colours_recorded_with_their_facts() -> None:
    result = dip_player(BAGRU, About())
    assert result.composed
    (component,) = result.components
    body = component.proposal
    assert (body.kind, body.label) == ("dip_player", "bagru-print/chemistry/colour-after-each-stage")
    spec = body.spec
    assert spec is not None
    assert [phase["pose"] for phase in spec["phases"]] == ["harda", "madder-bath", "washing"]
    assert spec["dips"] == ["--dye-harda", "--dye-madder"]
    assert spec["dipAgain"] == "Dip again"
    assert _fills(spec) == ["var(--dye-harda)", "var(--dye-madder)", "none"]
    assert delivery_problems(result.components) == []


def test_each_phase_says_its_colour_after_cited_by_the_fact_that_states_it() -> None:
    (component,) = dip_player(BAGRU, About()).components
    units = component.proposal.units
    texts = [units[phase["text"]] for phase in component.proposal.spec["phases"]]
    assert [(unit.text, unit.claim_ids) for unit in texts] == [
        ("Yellow", [claim(1)]),
        ("Red where alum was printed, black where syahi was", [claim(5)]),
        ("White: Pale", [claim(7)]),
    ]
    assert cited_claims(component) <= set(FACTS)


def test_a_colour_no_token_depicts_is_drawn_as_an_outline_its_colour_named_in_words() -> None:
    result = dip_player(BAGRU, About())
    spec = result.components[0].proposal.spec
    washing = spec["phases"][2]["drawing"]["children"][1]["attrs"]
    assert (washing["fill"], washing["stroke"], washing["stroke-dasharray"]) == (
        "none",
        "var(--ink-2)",
        "6 4",
    )
    assert spec["scene"]["children"][1]["attrs"]["fill"] == "none"
    assert result.left_out == (WASHING_IN_WORDS,)


def test_a_craft_with_no_recorded_colour_composes_its_dip_from_the_substances_its_stages_name() -> None:
    craft = unrecorded()
    assert all(stage.after is None or not stage.after.tokens for stage in craft.stages)
    result = dip_player(craft, About())
    assert result.composed, result.missing
    spec = result.components[0].proposal.spec
    assert [phase["pose"] for phase in spec["phases"]] == ["harda", "madder-bath", "washing", "yellow-dyeing"]
    assert spec["dips"] == ["--dye-harda", "--dye-madder", "--dye-turmeric"]
    assert _fills(spec) == ["var(--dye-harda)", "var(--dye-madder)", "none", "var(--dye-turmeric)"]
    assert spec["scene"]["children"][1]["attrs"]["fill"] == "var(--dye-turmeric)"
    assert result.left_out == (WASHING_IN_WORDS,)
    assert delivery_problems(result.components, craft) == []


def test_a_stage_whose_after_names_no_colour_is_left_out_of_the_dip_and_named() -> None:
    composed = dip_player(held(stages=(*BAGRU.stages, RINSING)), About())
    assert composed.composed
    assert [phase["pose"] for phase in composed.components[0].proposal.spec["phases"]] == [
        "harda",
        "madder-bath",
        "washing",
    ]
    assert composed.left_out == (WASHING_IN_WORDS, RINSING_NO_COLOUR)
    refused = dip_player(held(stages=(BAGRU.stages[0], RINSING)), About())
    assert refused.components == ()
    assert refused.missing == (
        "two stages of Bagru Print in a bath, each with its colour after naming the colours its fact states: "
        "Bagru-Print holds 1",
        RINSING_NO_COLOUR,
    )


def test_a_dip_with_no_colour_a_token_depicts_composes_nothing() -> None:
    washing = BAGRU.stages[4]
    rinsing = dataclasses.replace(RINSING, after=HeldAfter("Rinsed white", ("WHITE",), claim(7)))
    result = dip_player(held(stages=(washing, rinsing)), About())
    assert result.components == ()
    assert result.missing[0] == (
        "a depicted colour for one stage of Bagru Print at least: no specimen token shows a colour its stages "
        "name from the substances that give it, so the dip has no colour to draw"
    )
    assert result.missing[1:] == (
        WASHING_IN_WORDS,
        WASHING_IN_WORDS.replace("S05 (Washing)", "S07 (Rinsing)"),
    )


def test_fewer_than_two_stages_in_a_bath_compose_nothing_and_say_what_to_propose() -> None:
    result = dip_player(BAGRU, About(stage="S01"))
    assert result.components == ()
    assert result.missing[0].startswith("two stages of Bagru Print in a bath")
    plain = tuple(dataclasses.replace(stage, after=None) for stage in BAGRU.stages)
    gaps = dip_player(held(stages=plain), About()).missing
    assert any(
        gap.startswith("the colour after the stage S01 (Harda): propose_structure STAGE_AFTER")
        for gap in gaps
    )


def test_a_dip_about_a_material_holds_only_the_stages_that_use_it() -> None:
    assert dip_player(BAGRU, About(material="M09")).missing == (
        "the material M09: no stage of Bagru-Print in a bath uses it",
    )
    assert dip_player(BAGRU, About(material="M03")).components == ()
