import uuid
from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.services import matter_builders
from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.builder_interface import BuilderTools
from app.services.matter_builders import MaterialCardBuilder, MoleculeBuilder, ReactionPlayerBuilder
from app.sources.reference.pubchem import PubChemAdapter

from ..science.golden_process import ALIZARIN, claim_id
from ..sources.recorded import Recorder, Reply, fixed_clock, source_http
from ..voice.listen_fakes import MemoryObjects
from .fixtures import (
    ALIZARIN_RECORD,
    ALUM_OWN_CLAIM,
    PA_CLAIM,
    POTASSIUM_ALUM,
    CardModel,
    alizarin_record_source,
    chemistry_ask,
    matter,
)

GI_JOURNAL = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"
COLOURS_SOURCE = "4ce205e3-653f-51db-9e49-14fb3b3f2e14"
IRON_ACETATE_REACTION = uuid.UUID("d9643f49-fefc-5e3a-ad08-a5ae499a4161")
ALIZARIN_LAKE = uuid.UUID("26229ecd-184c-5adf-86d0-b45c56394f27")
PUG = "pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid"
ALIZARIN_SDF = Reply("pubchem_conformer.sdf")
NO_CONFORMER = Reply("pubchem_conformer_missing.txt", status=404)
CARD_REPLY = {"cards": [{"material": "m1", "facts": ["m1.c1", "m1.c7"], "handling": ["m1.c2", "m1.c1"]}]}


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    found: dict[str, Any] = {"matter": matter()}

    async def load(sessions: Any, craft: Any) -> Any:
        return found["matter"]

    monkeypatch.setattr(matter_builders, "craft_matter", load)
    return found


def tools(model: CardModel | None = None) -> BuilderTools:
    return BuilderTools(
        sessions=None, live=None, plan_model=model or CardModel(CARD_REPLY), compose_model=None
    )


def pubchem(routes: dict[str, Reply]) -> tuple[PubChemAdapter, Recorder]:
    recorder = Recorder(routes)
    return PubChemAdapter(source_http(recorder, "pubchem"), clock=fixed_clock()), recorder


def molecules(objects: MemoryObjects | None, adapter: PubChemAdapter) -> MoleculeBuilder:
    async def source() -> PubChemAdapter:
        return adapter

    return MoleculeBuilder(tools(), bucket=lambda: objects, pubchem=source)


async def test_the_reaction_player_plays_the_craft_s_stored_reactions(stored: dict[str, Any]) -> None:
    built = await ReactionPlayerBuilder(tools()).build(chemistry_ask())
    (player,) = built.blocks
    assert (player.id, [step.reaction_id for step in player.steps]) == (
        "s4.reactions",
        [IRON_ACETATE_REACTION, ALIZARIN_LAKE],
    )
    assert list(built.sources) == [COLOURS_SOURCE]
    assert built.sources[COLOURS_SOURCE]["id"] == COLOURS_SOURCE


async def test_an_answer_for_any_craft_gets_no_matter_blocks(stored: dict[str, Any]) -> None:
    ask = chemistry_ask(craft=False)
    for builder in (ReactionPlayerBuilder(tools()), MaterialCardBuilder(tools())):
        assert (await builder.build(ask)).blocks == ()


async def test_a_card_shows_the_stored_material_its_term_and_the_claims_the_model_sorted(
    stored: dict[str, Any],
) -> None:
    model = CardModel(CARD_REPLY)
    built = await MaterialCardBuilder(tools(model)).build(chemistry_ask())
    (card,) = built.blocks
    assert (card.id, card.name, card.material_kind, card.role) == (
        "s4.card1",
        "Alum (fatakdi)",
        "MORDANT",
        "MORDANT",
    )
    assert (card.compound_id, card.formula, card.pubchem_cid) == (POTASSIUM_ALUM, None, None)
    assert (card.term_key, card.local_names, card.wikidata_id) == (
        "alum",
        ["fatakdi", "fitkari", "karam"],
        None,
    )
    assert [(s.id, s.citations[0].claim_id) for s in card.facts] == [
        ("s4.card1.1", str(claim_id(ALUM_OWN_CLAIM)))
    ]
    assert [(s.id, s.citations[0].claim_id) for s in card.handling] == [
        ("s4.card1.2", str(claim_id(PA_CLAIM)))
    ]
    assert built.sources == {}
    (call,) = model.calls
    assert '<untrusted_source ref="m1" label="material">' in call["user"]
    assert "Also called: fatakdi, fitkari, karam" in call["user"]
    assert call["user"].count("<untrusted_source ref=") == 3


async def test_a_card_shows_a_formula_and_cid_only_from_its_pubchem_record(stored: dict[str, Any]) -> None:
    stored["matter"] = matter(alum_linked=True)
    (card,) = (await MaterialCardBuilder(tools()).build(chemistry_ask())).blocks
    assert (card.formula, card.pubchem_cid) == ("KAl(SO4)2·12H2O", 24856)


async def test_a_card_fact_without_a_claim_is_dropped(stored: dict[str, Any]) -> None:
    reply = {"cards": [{"material": "m1", "facts": ["m1.c9", "m2.c1"], "handling": ["m1.c1"]}]}
    assert (await MaterialCardBuilder(tools(CardModel(reply))).build(chemistry_ask())).blocks == ()
    stranger = {"cards": [{"material": "m4", "facts": ["m1.c1"], "handling": []}]}
    assert (await MaterialCardBuilder(tools(CardModel(stranger))).build(chemistry_ask())).blocks == ()


async def test_a_card_reply_off_its_schema_fails_the_builder(stored: dict[str, Any]) -> None:
    with pytest.raises(ExternalFailure, match="off its schema"):
        await MaterialCardBuilder(tools(CardModel({"cards": [{"material": "m1"}]}))).build(chemistry_ask())


async def test_a_named_compound_with_a_3d_conformer_becomes_a_molecule(stored: dict[str, Any]) -> None:
    objects = MemoryObjects()
    adapter, recorder = pubchem({f"{PUG}/6293/record/SDF": ALIZARIN_SDF})
    built = await molecules(objects, adapter).build(chemistry_ask())
    (molecule,) = built.blocks
    assert (molecule.id, molecule.compound_id, molecule.pubchem_cid) == ("s4.molecule", ALIZARIN, 6293)
    assert (molecule.name, molecule.formula, molecule.source_id) == ("Alizarin", "C14H8O4", ALIZARIN_RECORD)
    assert built.sources == {ALIZARIN_RECORD: alizarin_record_source()}
    assert len(recorder.requests) == 1 and "media/molecules/6293/conformer.json" in objects.stored


async def test_a_compound_without_a_3d_conformer_adds_no_molecule(stored: dict[str, Any]) -> None:
    adapter, recorder = pubchem({f"{PUG}/6293/record/SDF": NO_CONFORMER})
    assert (await molecules(MemoryObjects(), adapter).build(chemistry_ask())).blocks == ()
    assert len(recorder.requests) == 1


async def test_the_first_named_compound_with_a_conformer_is_drawn(stored: dict[str, Any]) -> None:
    stored["matter"] = matter(alum_linked=True)
    adapter, recorder = pubchem(
        {f"{PUG}/24856/record/SDF": NO_CONFORMER, f"{PUG}/6293/record/SDF": ALIZARIN_SDF}
    )
    (molecule,) = (await molecules(MemoryObjects(), adapter).build(chemistry_ask())).blocks
    assert molecule.pubchem_cid == 6293
    assert [request.url.path.split("/")[-3] for request in recorder.requests] == ["24856", "6293"]


async def test_a_kept_conformer_makes_no_second_pubchem_call(stored: dict[str, Any]) -> None:
    objects = MemoryObjects()
    first, _ = pubchem({f"{PUG}/6293/record/SDF": ALIZARIN_SDF})
    await molecules(objects, first).build(chemistry_ask())
    second, recorder = pubchem({})
    (molecule,) = (await molecules(objects, second).build(chemistry_ask())).blocks
    assert molecule.pubchem_cid == 6293 and recorder.requests == []


async def test_without_the_media_bucket_no_molecule_is_looked_up(stored: dict[str, Any]) -> None:
    adapter, recorder = pubchem({})
    assert (await molecules(None, adapter).build(chemistry_ask())).blocks == ()
    assert recorder.requests == []


async def test_the_registry_adds_the_built_matter_blocks(
    stored: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter, _ = pubchem({f"{PUG}/6293/record/SDF": ALIZARIN_SDF})

    async def live(*_: Any) -> PubChemAdapter:
        return adapter

    monkeypatch.setattr(matter_builders, "live_pubchem", live)
    monkeypatch.setattr(matter_builders, "media_bucket", MemoryObjects)
    builders = BlockBuilders.from_registry(tools(), BLOCK_BUILDERS)
    chemistry = await builders.added(chemistry_ask())
    assert [block.kind for block in chemistry.blocks] == ["reaction_player", "material_card", "molecule_3d"]
    assert set(chemistry.sources) == {GI_JOURNAL, COLOURS_SOURCE, ALIZARIN_RECORD}
    materials = await builders.added(chemistry_ask(discipline="MATERIALS"))
    assert [block.kind for block in materials.blocks] == ["material_card", "molecule_3d"]
