from app.research.blocks_play import SimulationBlock
from app.services.curation_keys import curated_id

from ..contracts.golden import golden_json
from .craft_mechanism import (
    AJRAKH,
    CRAFT_MECHANISM_GOLDEN,
    KUT_BLACK,
    built_craft_mechanism,
    craft_mechanism_golden,
    recorded_draft,
)
from .fixtures import OPUS

INPUTS = "craft.page.inputs.json"
KUT_REACTION = "R02"


async def test_the_craft_mechanism_golden_is_what_the_builder_makes_from_the_recorded_draft() -> None:
    block, golden = await built_craft_mechanism(recorded_draft())
    assert golden == craft_mechanism_golden()
    assert block.model == OPUS


def test_the_craft_mechanism_rests_on_the_kutch_ajrakh_dossier_alone() -> None:
    block = SimulationBlock.model_validate(craft_mechanism_golden()["block"])
    own = {str(curated_id(AJRAKH, f"C{n:03d}")) for n in range(1, 200)}
    assert {citation.claim_id for citation in block.citations()} <= own
    assert {ground.claim_id for ground in block.grounds} == {str(KUT_BLACK)}
    assert [str(reaction.reaction_id) for reaction in block.reactions] == [
        str(curated_id(AJRAKH, "reaction", KUT_REACTION))
    ]


def test_the_page_inputs_store_the_craft_mechanism_as_the_kut_explainer() -> None:
    (stored,) = golden_json(INPUTS)["explainers"]
    assert (stored["termKey"], stored["golden"]) == ("kut", CRAFT_MECHANISM_GOLDEN)
    assert craft_mechanism_golden()["block"]["hidden"] is False
