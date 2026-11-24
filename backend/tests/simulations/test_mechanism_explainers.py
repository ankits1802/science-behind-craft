import dataclasses
import json
import logging
import uuid
from typing import Any

import pytest

from app.composer.simulation import reaction_text
from app.research.blocks import ExplainerSentence, ImageItem, ImagesBlock, ProseBlock
from app.research.blocks_play import SimulationBlock
from app.research.media_refs import MediaRef
from app.research.sections import SectionSpec
from app.research.simulation_draft import OfferedReaction
from app.research.untrusted import untrusted_block
from app.science.mechanisms import section_concepts, simulation_reaction
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk
from app.services.simulation_grounding import AnswerConcepts, explainer_limit

from ..contracts.golden import golden_json
from ..matter.fixtures import PA_CLAIM, RED_CLAIM, chemistry_ask, matter, view
from ..science.golden_process import ALIZARIN, IRON_ACETATE, claim_id, golden_records, known_claim
from .at_the_bar import IRON_AT_THE_BAR
from .fixtures import OPUS, DraftModel, PictureSearches, builder, golden_block, golden_simulation

ALIZARIN_LAKE = uuid.UUID("26229ecd-184c-5adf-86d0-b45c56394f27")
IRON_REACTION = uuid.UUID("d9643f49-fefc-5e3a-ad08-a5ae499a4161")
IRON_CLAIM = "seed-e1a28b32e2c7416ebed3"
KUT_CLAIM = "seed-ca39189df4e04dcb5a7a"
MADDER_CLAIM = "seed-bd5ef6022d643b22c6dd"
LAKE_LABEL = "Alizarin binding to the alum mordant"
IRON_EQUATION = "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2"


def mechanism_golden() -> dict[str, Any]:
    return golden_json("explainer.simulation-mechanism.golden.json")


def mechanism_html() -> str:
    return IRON_AT_THE_BAR


def mechanism_draft(**changes: Any) -> dict[str, Any]:
    reply = {
        "build": True,
        "concept": "Iron dissolving into iron acetate",
        "title": "How scrap iron becomes the iron acetate of kut",
        "grounds": ["s1"],
        "reactions": ["r1"],
        "values": [],
        "html": mechanism_html(),
    }
    return reply | changes


def iron_ask(
    *, answer_id: uuid.UUID | None = None, section_id: str = "s2", depth: str = "EXPERT"
) -> BuildAsk:
    found = known_claim(IRON_CLAIM)
    prose = ProseBlock(
        id=f"{section_id}.b1",
        kind="prose",
        version=1,
        reuse=None,
        sentences=[
            ExplainerSentence(
                id=f"{section_id}.b1.1",
                text=found.text,
                level=found.level,
                citations=list(found.citations),
                terms=[],
            )
        ],
    )
    sources = golden_records().sources
    cited = CitedClaims(
        views={claim_id(IRON_CLAIM): view(IRON_CLAIM)},
        sources={
            sid: sources[sid].model_dump(mode="json", by_alias=True) for sid in prose.cited_source_ids()
        },
    )
    base = chemistry_ask()
    request = base.request.model_copy(update={"depth": depth})
    spec = SectionSpec(id=section_id, discipline="CHEMISTRY", title="The chemistry", order=2)
    return BuildAsk(answer_id or uuid.UUID(int=2), spec, request, (prose,), cited)


def concept_picture(block_id: str, claim: str) -> ImagesBlock:
    media = MediaRef.model_validate(
        {
            "id": "11111111-1111-5111-8111-111111111111",
            "display": "INLINE",
            "provider": "commons",
            "pageUrl": "https://commons.wikimedia.org/wiki/File:Alizarin.jpg",
            "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Alizarin.jpg",
            "width": None,
            "height": None,
            "credit": None,
            "sourceId": None,
            "title": "Alizarin crystals",
            "alt": "Red alizarin crystals",
            "author": "A photographer",
            "site": "commons.wikimedia.org",
            "licence": "CC BY-SA 4.0",
            "licenceUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
            "retrievedAt": "2026-11-18T10:00:00Z",
        }
    )
    return ImagesBlock(
        id=block_id,
        kind="images",
        version=1,
        reuse=None,
        items=[ImageItem(media=media, claim_ids=[claim_id(claim)], relevance="TEXT")],
    )


def test_the_chemistry_section_s_concept_is_the_stored_reaction_its_prose_cites() -> None:
    (concept,) = section_concepts(matter().records, chemistry_ask().blocks)
    assert (concept.key, concept.label) == (f"reaction:{ALIZARIN_LAKE}", LAKE_LABEL)
    assert [view.id for view in concept.reactions] == [ALIZARIN_LAKE]
    assert concept.shown_claim_ids == (claim_id(RED_CLAIM),)
    assert concept.words == ("Alizarin",)
    assert concept.position == 1


def test_a_sentence_naming_iron_acetate_finds_the_iron_reaction_and_its_balanced_equation() -> None:
    (concept,) = section_concepts(matter().records, iron_ask().blocks)
    assert concept.key == f"reaction:{IRON_REACTION}"
    reaction = simulation_reaction(concept.reactions[0])
    assert (reaction.equation, reaction.balanced) == (IRON_EQUATION, True)
    assert [(s.formula, s.coefficient) for s in reaction.species] == [
        ("Fe", 1),
        ("CH3COOH", 2),
        ("Fe(CH3COO)2", 1),
        ("H2", 1),
    ]
    assert reaction.coefficients() == [1, 2, 1, 1]
    assert {s.compound_id for s in reaction.species} == {None, IRON_ACETATE}


def test_reactions_sharing_a_species_word_are_one_concept() -> None:
    records = golden_records()
    lake, iron = sorted(records.reactions, key=lambda r: str(r.id) != str(ALIZARIN_LAKE))
    twin = dataclasses.replace(lake, id=uuid.UUID(int=77), ordinal=2, label="Alizarin fixed on the cloth")
    joined = dataclasses.replace(records, reactions=(lake, iron, twin))
    (concept,) = section_concepts(joined, chemistry_ask().blocks)
    assert [view.label for view in concept.reactions] == [LAKE_LABEL, "Alizarin fixed on the cloth"]
    assert ALIZARIN in {s.compound_id for view in concept.reactions for s in view.species}


async def test_the_brief_names_the_concept_and_carries_the_stored_reaction_as_data() -> None:
    model = DraftModel(
        [mechanism_draft(build=False, concept="", title="", grounds=[], reactions=[], html="")]
    )
    await builder(model, matter=matter()).build(chemistry_ask())
    (call,) = model.calls
    (lake,) = [r for r in golden_records().reactions if r.id == ALIZARIN_LAKE]
    (concept,) = section_concepts(matter().records, chemistry_ask().blocks)
    offered = OfferedReaction("r1", simulation_reaction(concept.reactions[0]))
    assert untrusted_block("concept", "concept to show", LAKE_LABEL) in call["user"]
    assert untrusted_block("r1", "reaction", reaction_text(offered)) in call["user"]
    assert (
        "Aluminium from the alum mordant (Al^3+) + Alizarin (C14H8O4) -> Aluminium-alizarin lake"
        in call["user"]
    )
    assert (
        "Equation: none, a formula is missing (not balanced, so show it as a word equation)." in call["user"]
    )
    texts = [known_claim(c).text for c in (RED_CLAIM, MADDER_CLAIM, PA_CLAIM)]
    assert [untrusted_block(f"s{n}", "statement", t) in call["user"] for n, t in enumerate(texts, 1)] == [
        True
    ] * 3
    assert lake.label == LAKE_LABEL


async def test_a_mechanism_explainer_needs_no_figure_when_its_statements_and_reaction_ground_it() -> None:
    explainer = DraftModel([mechanism_draft()])
    compose = DraftModel([])
    built = await builder(compose, matter=matter(), explainer=explainer).build(iron_ask())
    (block,) = built.blocks
    assert isinstance(block, SimulationBlock)
    assert compose.calls == [] and len(explainer.calls) == 1
    assert (block.values, block.model) == ([], OPUS)
    assert [r.reaction_id for r in block.reactions] == [IRON_REACTION]
    assert block.reactions[0].equation == IRON_EQUATION
    assert [c.claim_id for c in block.grounds] == [str(claim_id(IRON_CLAIM))]
    golden = mechanism_golden()
    assert set(built.sources) == {s["id"] for s in golden["sources"]} - set(iron_ask().cited.sources)


async def test_a_coefficient_shown_without_its_reaction_is_refused_and_the_redraft_is_told(
    caplog: pytest.LogCaptureFixture,
) -> None:
    explainer = DraftModel(
        [mechanism_draft(reactions=[]), mechanism_draft(reactions=["r9"]), mechanism_draft()]
    )
    with caplog.at_level(logging.INFO):
        built = await builder(DraftModel([]), matter=matter(), explainer=explainer).build(iron_ask())
    assert built.blocks == ()
    assert "NUMBER: 2 shown but not a data value" in explainer.calls[1]["user"]
    assert len(explainer.calls) == 2


async def test_an_unknown_reaction_is_a_ground_problem_and_a_redraft_that_fixes_it_is_kept() -> None:
    explainer = DraftModel([mechanism_draft(reactions=["r9"]), mechanism_draft()])
    built = await builder(DraftModel([]), matter=matter(), explainer=explainer).build(iron_ask())
    (block,) = built.blocks
    assert [r.reaction_id for r in block.reactions] == [IRON_REACTION]
    assert "GROUND: r9 is not an offered reaction" in explainer.calls[1]["user"]


async def test_a_concept_the_model_declines_gets_its_own_picture() -> None:
    model = DraftModel(
        [mechanism_draft(build=False, concept="", title="", grounds=[], reactions=[], html="")]
    )
    pictures = PictureSearches(found={f"reaction:{ALIZARIN_LAKE}": concept_picture("x", RED_CLAIM)})
    built = await builder(model, matter=matter(), pictures=pictures).build(chemistry_ask())
    (block,) = built.blocks
    assert (block.kind, block.id) == ("images", "s4.concept1")
    assert pictures.asked == [(f"reaction:{ALIZARIN_LAKE}", "Alizarin", (claim_id(RED_CLAIM),))]


async def test_one_answer_explains_a_concept_once_and_never_also_pictures_it() -> None:
    answer = uuid.UUID(int=9)
    explainer = DraftModel([mechanism_draft()])
    pictures = PictureSearches(found={f"reaction:{IRON_REACTION}": concept_picture("x", IRON_CLAIM)})
    shared = builder(DraftModel([]), matter=matter(), explainer=explainer, pictures=pictures)
    first = await shared.build(iron_ask(answer_id=answer, section_id="s2"))
    second = await shared.build(iron_ask(answer_id=answer, section_id="s5"))
    assert [b.kind for b in first.blocks] == ["simulation"]
    assert second.blocks == () and pictures.asked == [] and len(explainer.calls) == 1


async def test_past_the_answer_s_limit_a_concept_is_pictured_instead_and_asks_no_model() -> None:
    answer = uuid.UUID(int=10)
    explainer = DraftModel([mechanism_draft()])
    pictures = PictureSearches(found={f"reaction:{IRON_REACTION}": concept_picture("x", IRON_CLAIM)})
    shared = builder(DraftModel([]), matter=matter(), explainer=explainer, pictures=pictures)
    shared._answers[answer] = AnswerConcepts(0)
    built = await shared.build(iron_ask(answer_id=answer))
    assert [b.kind for b in built.blocks] == ["images"]
    assert explainer.calls == []


def test_each_depth_allows_its_own_number_of_explainers() -> None:
    assert [explainer_limit(d) for d in ("BASIC", "DETAILED", "EXPERT", None)] == [1, 2, 3, 3]
    answer = AnswerConcepts(2)
    assert [answer.take(k) for k in ("a", "a", "b", "c")] == [True, False, True, False]
    answer.give_back("b")
    assert (answer.picture("b"), answer.picture("b"), answer.take("b"), answer.picture("a")) == (
        True,
        False,
        False,
        False,
    )


def test_the_mechanism_golden_is_a_valid_explainer_resting_on_statements_and_a_reaction() -> None:
    golden = mechanism_golden()
    block = SimulationBlock.model_validate(golden["block"])
    assert block.values == [] and block.reactions[0].equation == IRON_EQUATION
    assert block.model_dump(mode="json", by_alias=True) == golden["block"]
    assert {c.source_id for c in block.citations()} == {s["id"] for s in golden["sources"]}
    old = golden_block().model_dump(mode="json", by_alias=True)
    assert (
        "grounds" not in old and "reactions" not in old and json.dumps(old) == json.dumps(golden_simulation())
    )


@pytest.mark.parametrize(
    ("changes", "detail"),
    [
        ({"grounds": [], "reactions": []}, "cites nothing"),
        ({"reactionsEquation": "Fe + CH3COOH -> Fe(CH3COO)2 + H2"}, "equation is not built from its species"),
    ],
)
def test_a_mechanism_explainer_off_its_grounding_does_not_construct(
    changes: dict[str, Any], detail: str
) -> None:
    payload = dict(mechanism_golden()["block"])
    if "reactionsEquation" in changes:
        payload["reactions"] = [{**payload["reactions"][0], "equation": changes["reactionsEquation"]}]
    else:
        payload |= changes
    with pytest.raises(ValueError, match=detail):
        SimulationBlock.model_validate(payload)
