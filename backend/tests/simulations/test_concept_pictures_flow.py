import dataclasses
from typing import Any

from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders, BuilderEntry
from app.services.builder_interface import BuildAsk, Built
from app.services.claim_ledger import ClaimLedger

from ..matter.fixtures import RED_CLAIM, chemistry_ask
from .test_mechanism_explainers import concept_picture


@dataclasses.dataclass
class PictureBuilder:
    blocks: tuple[Any, ...]

    async def build(self, ask: BuildAsk) -> Built:
        return Built(self.blocks, {})


def test_only_the_generated_explainer_s_builder_adds_pictures() -> None:
    adding = [entry.kind for entry in BLOCK_BUILDERS if entry.adds_pictures]
    assert adding == ["simulation"]


async def test_a_concept_picture_from_the_explainer_builder_is_added_and_another_kind_s_is_refused() -> None:
    picture = concept_picture("s4.concept1", RED_CLAIM)
    (simulation,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "simulation"]
    cards = BuilderEntry("material_card", frozenset({"CHEMISTRY"}), lambda tools: PictureBuilder(()), 1.0)
    builders = BlockBuilders(
        [(simulation, PictureBuilder((picture,))), (cards, PictureBuilder((picture.model_copy(),)))]
    )
    added = await builders.added(chemistry_ask())
    assert [(block.kind, block.id) for block in added.blocks] == [("images", "s4.concept1")]


def test_the_ledger_shows_a_concept_picture_beside_the_section_picture_once_each() -> None:
    ask = chemistry_ask()
    ledger = ClaimLedger()
    (prose,) = ledger.admit("s4", list(ask.blocks), ask.cited.sources)
    concept = ledger.admit("s4", [concept_picture("s4.b2", RED_CLAIM)], {})
    again = ledger.admit("s4", [concept_picture("s4.b3", RED_CLAIM)], {})
    assert prose.kind == "prose"
    assert [block.kind for block in concept] == ["images"]
    assert again == []
