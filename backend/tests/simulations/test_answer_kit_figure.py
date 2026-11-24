from app.research.blocks_kit import KitFigureBlock
from app.research.blocks_play import SimulationBlock
from app.research.component_specs_kit import BathPart, ClothPart
from app.science.kit_figures import concept_kit_figure
from app.science.mechanisms import section_concepts
from app.services.block_builders import BLOCK_BUILDERS, built_by_registry
from app.services.curation_keys import curated_id

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


def test_the_generated_explainer_s_builder_may_draw_a_kit_figure_in_its_place() -> None:
    (entry,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "simulation"]
    assert entry.draws == frozenset({"kit_figure"}) and entry.adds_pictures
    assert {"simulation", "kit_figure"} <= built_by_registry()
    assert [other.kind for other in BLOCK_BUILDERS if other.draws] == ["simulation"]
