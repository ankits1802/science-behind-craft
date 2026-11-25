from dataclasses import replace

from app.research.blocks_kit import KitFigureBlock
from app.research.blocks_play import SimulationBlock
from app.research.component_specs_kit import BathPart, ClothPart
from app.science.kit_figures import concept_kit_figure
from app.science.mechanisms import section_concepts
from app.services.block_builders import BLOCK_BUILDERS, built_by_registry
from app.services.builder_interface import BuildAsk
from app.services.craft_matter import CraftMatter
from app.services.curation_keys import curated_id
from app.services.simulation_grounding import AnswerConcepts

from .at_the_bar import KUT_AT_THE_BAR
from .craft_mechanism import AJRAKH, ajrakh_matter_and_ask, recorded_draft
from .fixtures import DraftModel, builder

OXIDISED = curated_id(AJRAKH, "C086")
INDIGO_REACTION = curated_id(AJRAKH, "reaction", "R01")
KUT_REACTION = curated_id(AJRAKH, "reaction", "R02")
INDIGO_QUESTION = "Why does the cloth from the indigo vat turn from green to blue?"
CHANGE_QUOTE = (
    "At first bright green, the cloth rapidly becomes blue as oxygen meets the dye particles on the fibres."
)


def indigo() -> tuple[KitFigureBlock | None, list[str]]:
    matter, ask = ajrakh_matter_and_ask(OXIDISED, INDIGO_QUESTION)
    (concept,) = [
        c for c in section_concepts(matter.records, ask.blocks) if c.key == f"reaction:{INDIGO_REACTION}"
    ]
    quotes = [citation.id for citation in matter.records.claims[OXIDISED].citations]
    return concept_kit_figure(concept, matter.records, block_id="s1.kit"), quotes


def test_the_vat_s_stated_change_of_colour_is_composed_as_a_before_and_after_from_the_kit() -> None:
    figure, _ = indigo()
    assert figure is not None
    texts = {label.ref: label.text for label in figure.labels}
    assert texts == {
        "u0001": "Green to blue",
        "u0002": "Cloth drawn green in the vat, then blue",
        "u0003": "Green",
        "u0004": "Cloth in the vat",
        "u0005": "Blue",
        "u0006": "Cloth, blue",
    }
    diagram = figure.diagram
    assert (diagram.layout, diagram.head.title, diagram.alt) == ("before_after", "u0001", "u0002")
    assert [(panel.label, panel.motion) for panel in diagram.panels] == [("u0003", "dip"), ("u0005", "take")]
    ((bath,), (cloth,)) = (diagram.panels[0].parts, diagram.panels[1].parts)
    assert isinstance(bath, BathPart) and isinstance(cloth, ClothPart)
    assert (bath.vessel, bath.piece, bath.liquor, bath.label) == ("vat", "--dye-leuco", None, "u0004")
    assert (cloth.form, cloth.material, cloth.label) == ("length", "--dye-indigo", "u0006")


def test_each_part_of_the_vat_figure_cites_the_quote_that_states_it() -> None:
    figure, quotes = indigo()
    assert figure is not None
    cited = {label.ref: [c.id for c in label.citations] for label in figure.labels}
    (change,) = next(c for c in figure.labels if c.ref == "u0006").citations
    assert change.quote == CHANGE_QUOTE
    assert sorted(cited["u0004"]) == sorted(quotes) and cited["u0006"] == [change.id]
    assert cited["u0001"] == cited["u0002"] == cited["u0003"] == cited["u0005"] == []
    assert {c.claim_id for c in figure.citations()} == {str(OXIDISED)}


async def test_an_answer_that_draws_its_figure_from_the_kit_asks_no_model_at_all() -> None:
    matter, ask = ajrakh_matter_and_ask(OXIDISED, INDIGO_QUESTION)
    explainer, compose = DraftModel([]), DraftModel([])
    built = await builder(compose, matter=matter, explainer=explainer).build(ask)
    (block,) = built.blocks
    assert isinstance(block, KitFigureBlock) and block.id == "s1.kit"
    assert explainer.calls == [] and compose.calls == []
    assert set(built.sources) <= set(matter.records.sources)


async def test_a_mechanism_whose_sentences_state_no_change_of_colour_is_still_asked_of_the_model_once() -> (
    None
):
    matter, ask = ajrakh_matter_and_ask()
    (concept,) = [
        c for c in section_concepts(matter.records, ask.blocks) if c.key == f"reaction:{KUT_REACTION}"
    ]
    assert concept_kit_figure(concept, matter.records, block_id="s1.kit") is None
    explainer = DraftModel([recorded_draft() | {"html": KUT_AT_THE_BAR}])
    (block,) = (await builder(DraftModel([]), matter=matter, explainer=explainer).build(ask)).blocks
    assert isinstance(block, SimulationBlock) and len(explainer.calls) == 1


def basic_sections() -> tuple[CraftMatter, BuildAsk, BuildAsk]:
    matter, kut = ajrakh_matter_and_ask()
    _, vat = ajrakh_matter_and_ask(OXIDISED, INDIGO_QUESTION)
    basic = kut.request.model_copy(update={"depth": "BASIC"})
    return matter, replace(kut, request=basic), replace(vat, request=basic)


def second(ask: BuildAsk) -> BuildAsk:
    return replace(ask, section=ask.section.model_copy(update={"id": "s2"}))


async def test_a_section_draws_its_kit_figure_after_the_answer_s_generated_explainers_are_spent() -> None:
    matter, kut, vat = basic_sections()
    explainer = DraftModel([recorded_draft() | {"html": KUT_AT_THE_BAR}])
    build = builder(DraftModel([]), matter=matter, explainer=explainer)
    (explained,) = (await build.build(kut)).blocks
    assert isinstance(explained, SimulationBlock) and len(explainer.calls) == 1
    (figure,) = (await build.build(second(vat))).blocks
    assert isinstance(figure, KitFigureBlock) and figure.id == "s2.kit"
    assert len(explainer.calls) == 1


async def test_a_kit_figure_leaves_the_answer_s_generated_explainer_to_another_section() -> None:
    matter, kut, vat = basic_sections()
    explainer = DraftModel([recorded_draft() | {"html": KUT_AT_THE_BAR}])
    build = builder(DraftModel([]), matter=matter, explainer=explainer)
    (figure,) = (await build.build(vat)).blocks
    assert isinstance(figure, KitFigureBlock) and explainer.calls == []
    (explained,) = (await build.build(second(kut))).blocks
    assert isinstance(explained, SimulationBlock) and len(explainer.calls) == 1


async def test_a_reused_section_below_expert_draws_its_kit_figure_and_asks_no_model() -> None:
    matter, kut, vat = basic_sections()
    explainer, compose = DraftModel([]), DraftModel([])
    drawing = builder(compose, matter=matter, explainer=explainer).drawing()
    (figure,) = (await drawing.build(vat)).blocks
    assert isinstance(figure, KitFigureBlock) and figure.id == "s1.kit"
    assert (await drawing.build(second(kut))).blocks == ()
    assert explainer.calls == [] and compose.calls == []


async def test_a_concept_a_reused_section_drew_is_not_drawn_again_in_the_same_answer() -> None:
    matter, _, vat = basic_sections()
    build = builder(DraftModel([]), matter=matter, explainer=DraftModel([]))
    (figure,) = (await build.drawing().build(vat)).blocks
    assert isinstance(figure, KitFigureBlock)
    again = (await build.drawing().build(second(vat))).blocks
    assert not [b for b in again if isinstance(b, KitFigureBlock) and b.diagram == figure.diagram]


async def test_a_section_draws_no_kit_figure_of_a_change_its_own_prose_does_not_state() -> None:
    matter, kut, vat = basic_sections()
    (said,) = vat.blocks
    beside = said.model_copy(update={"id": "s1.b2", "kind": "zoom_story"})
    ask = replace(kut, blocks=(*kut.blocks, beside))
    assert f"reaction:{INDIGO_REACTION}" in {c.key for c in section_concepts(matter.records, ask.blocks)}
    build = builder(DraftModel([]), matter=matter, explainer=DraftModel([]))
    assert (await build.drawing().build(ask)).blocks == ()
    (figure,) = (await build.drawing().build(second(vat))).blocks
    assert isinstance(figure, KitFigureBlock)


def test_one_concept_is_drawn_once_and_never_also_built_or_pictured() -> None:
    answer = AnswerConcepts(limit=1)
    assert answer.draw("reaction:vat")
    assert not answer.draw("reaction:vat")
    assert not answer.take("reaction:vat") and not answer.picture("reaction:vat")
    assert answer.take("reaction:kut") and not answer.take("reaction:other")


def test_the_generated_explainer_s_builder_may_draw_a_kit_figure_in_its_place() -> None:
    (entry,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "simulation"]
    assert entry.draws == frozenset({"kit_figure"}) and entry.adds_pictures
    assert {"simulation", "kit_figure"} <= built_by_registry()
    assert [other.kind for other in BLOCK_BUILDERS if other.draws] == ["simulation"]
