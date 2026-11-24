import dataclasses

from app.services.compose_held import About
from app.services.compose_reaction import reaction_player

from .held import AJRAKH_FACT, BAGRU, FACTS, SLUG, cited_claims, claim, delivery_problems, held

SUB = "sub"


def test_a_reaction_player_steps_through_the_craft_s_own_reactions_in_the_order_of_their_stages() -> None:
    result = reaction_player(BAGRU, About())
    assert result.composed
    (component,) = result.components
    body = component.proposal
    assert (body.kind, body.label, body.craft_slug) == (
        "reaction_player",
        "bagru-print/chemistry/reactions-step-by-step",
        SLUG,
    )
    assert [subject.model_dump() for subject in body.subjects] == [{"kind": "CRAFT", "key": SLUG}]
    spec = body.spec
    assert spec is not None
    assert [step["name"] for step in spec["steps"]] == ["Syahi", "Black printing", "Madder bath"]
    assert spec["current"] == 3 and spec["key"] is None and len(spec["scenes"]) == 1
    assert result.left_out == (
        "a fact of Bagru-Print's own for the reaction R03, which rests on no fact the page shows",
    )
    assert delivery_problems(result.components) == []


def test_every_unit_cites_only_the_craft_s_own_facts_and_a_fact_of_another_page_is_never_cited() -> None:
    (component,) = reaction_player(BAGRU, About()).components
    cited = cited_claims(component)
    assert cited <= set(FACTS) and AJRAKH_FACT not in cited
    texts = {unit.text for unit in component.proposal.units.values() if unit.claim_ids}
    assert FACTS[claim(4)] in texts and FACTS[claim(2)] in texts and FACTS[claim(3)] in texts


def test_a_step_the_server_balanced_shows_its_equation_and_the_others_say_why_they_have_none() -> None:
    (component,) = reaction_player(BAGRU, About()).components
    body = component.proposal
    syahi, black, _ = body.spec["steps"]
    lane, equation = syahi["chemistry"]["parts"]
    assert lane["part"] == "lane" and equation["part"] == "equation"
    line = equation["equation"]["line"]
    assert [term["formula"] for term in line["reactants"]] == [
        ["Fe"],
        ["2 CH", {"text": "3", "style": SUB}, "COOH"],
    ]
    assert [term["formula"] for term in line["products"]] == [
        ["Fe(CH", {"text": "3", "style": SUB}, "COO)", {"text": "2", "style": SUB}],
        ["H", {"text": "2", "style": SUB}],
    ]
    assert equation["equation"]["label"] == "iron and acetic acid gives iron(II) acetate and hydrogen"
    none = black["chemistry"]["parts"][1]
    assert none["part"] == "none"
    assert body.units[none["unit"]].text == "Named as the sources name it, without an equation."


def test_a_species_takes_its_material_s_recorded_colour_and_record_or_is_drawn_as_an_outline() -> None:
    (component,) = reaction_player(BAGRU, About()).components
    lanes = [step["chemistry"]["parts"][0]["items"] for step in component.proposal.spec["steps"]]
    species = {
        item["name"][0]: (item["swatch"], item["cid"])
        for lane in lanes
        for item in lane
        if item["item"] == "species"
    }
    assert species["syahi"] == ("--dye-kut", None)
    assert species["alizarin"] == ("--dye-madder", 6293)
    assert species["tannin"] == ("clear", None)


def test_a_stage_s_stated_time_is_the_step_s_condition_cited_by_its_fact() -> None:
    (component,) = reaction_player(BAGRU, About()).components
    body = component.proposal
    *_, madder = body.spec["steps"]
    (condition,) = madder["text"]["conditions"]
    assert body.units[condition["term"]].text == "Time"
    value = body.units[condition["value"]]
    assert (value.text, value.claim_ids) == ("an hour and a half", [claim(6)])


def test_the_player_rests_on_the_reaction_it_is_about_and_the_scene_shows_that_step_alone() -> None:
    (component,) = reaction_player(BAGRU, About(reaction="R01")).components
    spec = component.proposal.spec
    assert spec["current"] == 2
    groups = [child for child in spec["scenes"][0]["children"] if child["tag"] == "g"]
    assert [(group["attrs"]["data-on"], group["attrs"].get("class")) for group in groups] == [
        ("1", "off"),
        ("2", None),
        ("3", "off"),
    ]


def test_a_craft_with_no_reactions_gets_none_and_is_told_which_structure_to_propose() -> None:
    result = reaction_player(held(reactions=()), About())
    assert not result.composed and result.components == ()
    (missing,) = result.missing
    assert "propose_structure REACTION" in missing and SLUG in missing


def test_reactions_resting_only_on_another_page_s_facts_compose_nothing() -> None:
    foreign = tuple(dataclasses.replace(reaction, claim_ids=(AJRAKH_FACT,)) for reaction in BAGRU.reactions)
    result = reaction_player(held(reactions=foreign), About())
    assert result.components == ()
    assert result.missing[0].startswith("two reactions stated by Bagru Print's own facts")
    assert len(result.missing) == 1 + len(foreign)


def test_one_reaction_is_not_a_player_and_an_unknown_key_is_named() -> None:
    one = reaction_player(BAGRU, About(stage="S03"))
    assert one.components == () and "holds only R01" in one.missing[0]
    unknown = reaction_player(BAGRU, About(reaction="R09"))
    assert unknown.components == ()
    assert unknown.missing[0] == "the reaction R09: Bagru-Print holds no reaction of its own under that key"
