import dataclasses
import re
import uuid

from app.composer.what_if import what_if_message, what_if_schema
from app.research.structured import schema_problems
from app.research.untrusted import UNTRUSTED_TAG
from app.services.craft_matter import section_sentences
from app.services.what_if_evidence import WhatIfEvidence
from app.services.what_if_offers import (
    OfferedInput,
    OfferedOption,
    group_concepts,
    named_groups,
    what_if_brief,
    what_if_inputs,
)

from ..science.golden_process import claim_id, stage_id
from .fixtures import (
    AL_ROOT_ID,
    ALIZARIN_CONCEPT,
    ALIZARIN_ID,
    ALIZARIN_LAKE,
    CONTRAST,
    ICI_POWDER,
    LAKE_MECHANISM,
    MADDER_CONCEPT,
    MADDER_ID,
    MADDER_ROOTS,
    MADDER_WITH_INDIGO,
    RED,
    RED_STAGE,
    SHIFT,
    SYNTHESISED,
    TAPANO,
    WASHING_HYPOTHESIS,
    concept,
    evidence,
    red_ask,
    red_matter,
)

UNTRUSTED_BLOCK = re.compile(rf"<{UNTRUSTED_TAG} [^>]*>\n.*?\n</{UNTRUSTED_TAG}>", re.DOTALL)


def offered(found: WhatIfEvidence | None = None) -> list[OfferedInput]:
    matter = red_matter()
    ask = red_ask()
    groups = named_groups(matter, section_sentences(ask.blocks))
    return what_if_inputs(groups, matter, found or evidence(), ask.cited)


def claims_of(option: OfferedOption) -> list[tuple[uuid.UUID, str | None, uuid.UUID | None]]:
    return [(o.claim.id, o.relation, o.reaction_id) for o in option.outcomes]


def test_the_red_stage_s_dyes_are_one_input_and_the_section_names_its_first_options() -> None:
    (red,) = offered()
    assert (red.ref, red.stage.id, red.role) == ("i1", stage_id(RED), "DYE")
    assert [(option.ref, option.material.material_id) for option in red.options] == [
        ("i1.o1", MADDER_ID),
        ("i1.o2", ALIZARIN_ID),
        ("i1.o3", AL_ROOT_ID),
    ]
    groups = named_groups(red_matter(), section_sentences(red_ask().blocks))
    assert set(group_concepts(groups)) == {concept(MADDER_CONCEPT), concept(ALIZARIN_CONCEPT)}


def test_each_option_is_offered_its_relationships_then_its_own_facts_then_its_compound_s_reactions() -> None:
    madder, alizarin, al_root = offered()[0].options
    own_madder = sorted([claim_id(MADDER_ROOTS), claim_id(MADDER_WITH_INDIGO)])
    assert claims_of(madder) == [
        (claim_id(CONTRAST), "CONTRASTS_WITH", None),
        (claim_id(TAPANO), "DEPENDS_ON", None),
        *[(claim, None, None) for claim in own_madder],
    ]
    assert claims_of(alizarin) == [
        (claim_id(CONTRAST), "CONTRASTS_WITH", None),
        (claim_id(SHIFT), "ENABLES", None),
        (claim_id(SYNTHESISED), None, None),
        (claim_id(ICI_POWDER), None, None),
        (claim_id(RED_STAGE), None, ALIZARIN_LAKE),
        (claim_id(LAKE_MECHANISM), None, ALIZARIN_LAKE),
    ]
    assert al_root.outcomes == ()
    assert [o.ref for o in alizarin.outcomes] == [f"i1.o2.e{n}" for n in range(1, 7)]


def test_a_reaction_claim_that_names_neither_the_option_nor_its_compound_is_not_its_outcome() -> None:
    alizarin = offered()[0].options[1]
    assert claim_id(MADDER_ROOTS) not in {o.claim.id for o in alizarin.outcomes}


def test_options_are_only_materials_a_stored_text_or_a_contrast_relates_as_alternatives() -> None:
    without_contrast = dataclasses.replace(
        evidence(),
        relationships=tuple(r for r in evidence().relationships if r.claim_id != claim_id(CONTRAST)),
    )
    (red,) = offered(without_contrast)
    assert [option.material.material_id for option in red.options] == [ALIZARIN_ID, AL_ROOT_ID]


def test_a_section_naming_none_of_a_stage_s_materials_offers_no_input() -> None:
    ask = red_ask(keys=(MADDER_WITH_INDIGO,))
    assert named_groups(red_matter(), section_sentences(ask.blocks)) == []


def test_a_hypothesis_relationship_is_offered_marked_and_a_hypothesis_about_the_option_is_not() -> None:
    hypothesis = evidence(hypothesis=True)
    alizarin = offered(hypothesis)[0].options[1]
    (washing,) = [o for o in alizarin.outcomes if o.claim.id == claim_id(WASHING_HYPOTHESIS)]
    assert (washing.ref, washing.relation, washing.claim.level, washing.hypothesis) == (
        "i1.o2.e2",
        "CAUSES",
        "HYPOTHESIS",
        True,
    )
    owned = {**hypothesis.concept_claims, concept(MADDER_CONCEPT): (claim_id(WASHING_HYPOTHESIS),)}
    madder = offered(dataclasses.replace(hypothesis, concept_claims=owned))[0].options[0]
    assert claim_id(WASHING_HYPOTHESIS) not in {o.claim.id for o in madder.outcomes}


def test_the_brief_holds_stored_text_only_in_untrusted_blocks_and_marks_hypotheses_outside_them() -> None:
    message = what_if_message(what_if_brief(red_ask(), offered(evidence(hypothesis=True))))
    outside = UNTRUSTED_BLOCK.sub("", message)
    for stored in ("Indian madder", "Synthetic alizarin", "Al root", "madder or alizarin", "Tapano"):
        assert stored in message and stored not in outside
    assert "i1.o2.e2: a hypothesis, a stored relation (causes)" in outside
    assert "i1.o2.e1: a stated finding, a stored relation (contrasts with)" in outside
    assert "i1.o2.e6: a stated finding, cited by a stored reaction of the option's compound" in outside
    assert "Input i1: the dye of that stage." in outside


def test_the_reply_schema_is_one_a_structured_output_route_accepts() -> None:
    assert schema_problems(what_if_schema()) == []
