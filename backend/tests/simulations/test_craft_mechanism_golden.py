import logging

import pytest

from app.research.blocks_play import SimulationBlock
from app.services.curation_keys import curated_id

from ..contracts.golden import golden_json
from .at_the_bar import KUT_AT_THE_BAR, at_the_bar
from .craft_mechanism import (
    AJRAKH,
    CRAFT_MECHANISM_GOLDEN,
    KUT_BLACK,
    ajrakh_matter_and_ask,
    built_craft_mechanism,
    craft_mechanism_golden,
    recorded_draft,
)
from .fixtures import OPUS, DraftModel, builder

INPUTS = "craft.page.inputs.json"
KUT_REACTION = "R02"


async def test_the_recorded_draft_falls_below_the_bar_and_is_left_out_after_its_one_redraft(
    caplog: pytest.LogCaptureFixture,
) -> None:
    matter, ask = ajrakh_matter_and_ask()
    explainer = DraftModel([recorded_draft()])
    with caplog.at_level(logging.WARNING):
        built = await builder(DraftModel([]), matter=matter, explainer=explainer).build(ask)
    assert built.blocks == ()
    assert len(explainer.calls) == 2
    assert "ART: names the colour '#1d1b16'" in explainer.calls[1]["user"]
    assert any("rules failed: ART;" in record.getMessage() for record in caplog.records)


async def test_the_recorded_draft_redrawn_at_the_bar_is_the_golden_with_its_own_markup() -> None:
    block, golden = await built_craft_mechanism(recorded_draft() | {"html": KUT_AT_THE_BAR})
    expected = craft_mechanism_golden()
    expected["block"] = expected["block"] | at_the_bar(KUT_AT_THE_BAR)
    assert golden == expected
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
