import dataclasses

from app.services.compose_dip import dip_player
from app.services.compose_held import About

from .held import BAGRU, FACTS, cited_claims, claim, delivery_problems, held


def test_a_dip_player_plays_the_craft_s_bath_stages_in_the_colours_recorded_with_their_facts() -> None:
    result = dip_player(BAGRU, About())
    assert result.composed
    (component,) = result.components
    body = component.proposal
    assert (body.kind, body.label) == ("dip_player", "bagru-print/chemistry/colour-after-each-stage")
    spec = body.spec
    assert spec is not None
    assert [phase["pose"] for phase in spec["phases"]] == ["harda", "madder-bath"]
    assert spec["dips"] == ["--dye-harda", "--dye-madder"]
    assert spec["dipAgain"] == "Dip again"
    fills = [phase["drawing"]["children"][1]["attrs"]["fill"] for phase in spec["phases"]]
    assert fills == ["var(--dye-harda)", "var(--dye-madder)"]
    assert spec["scene"]["children"][1]["attrs"]["fill"] == "var(--dye-madder)"
    assert delivery_problems(result.components) == []


def test_each_phase_says_its_colour_after_cited_by_the_fact_that_states_it() -> None:
    (component,) = dip_player(BAGRU, About()).components
    units = component.proposal.units
    texts = [units[phase["text"]] for phase in component.proposal.spec["phases"]]
    assert [(unit.text, unit.claim_ids) for unit in texts] == [
        ("Yellow", [claim(1)]),
        ("Red where alum was printed, black where syahi was", [claim(5)]),
    ]
    assert cited_claims(component) <= set(FACTS)


def test_a_stage_whose_colour_after_has_no_recorded_colour_is_left_out_and_named() -> None:
    result = dip_player(BAGRU, About())
    assert result.left_out == (
        "a depicted colour recorded with the fact that states the colour after the stage S05 (Washing): ask the "
        "team for its specimen token, since a dip draws a stage only in the colour its fact states",
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
