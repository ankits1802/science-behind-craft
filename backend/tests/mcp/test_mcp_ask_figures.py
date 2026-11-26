import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from app.core.errors import ExternalFailure, NotConfigured
from app.research.blocks import BlockBase
from app.research.explainer import Block
from app.research.mcp_ask import AskedAnswer, AskedSection
from app.research.mcp_ask_figures import (
    COLOUR_SPECIMENS,
    AskedFigure,
    AskedMolecule,
    AskedPlayer,
    AskedTimeline,
    section_figures,
)
from app.science.molecule_conformer import conformer_geometry
from app.services.mcp_ask_molecules import drawn_molecules

from ..contracts.golden import REPO, golden_json

BLOCKS = TypeAdapter(Block)
SDF = (REPO / "backend" / "tests" / "sources" / "fixtures" / "pubchem_conformer.sdf").read_text(
    encoding="utf-8"
)
FIGURES_GOLDEN = "mcp.ask-figures.golden.json"
ALIZARIN = 6293
WEB_FILLS = REPO / "frontend" / "lib" / "reactionPlayer.ts"


def blocks(name: str, section_id: str) -> list[BlockBase]:
    (section,) = [section for section in golden_json(name)["sections"] if section["id"] == section_id]
    return [BLOCKS.validate_python(block) for block in section["blocks"]]


def figures(found: list[BlockBase]) -> list[Any]:
    sentences = [sentence for block in found for sentence in block.cited_sentences()]
    return section_figures(found, {sentence.id: at for at, sentence in enumerate(sentences)})


def test_a_reaction_player_plays_each_step_with_its_species_its_colours_and_its_own_sentences() -> None:
    player, molecule = figures(blocks("explainer.phase-b.golden.json", "s4"))
    assert isinstance(player, AskedPlayer) and player.kind == "reaction"
    assert [step.label for step in player.steps] == [
        "Scrap iron dissolving into iron acetate",
        "Indigo reduced to soluble leucoindigo in the vat",
        "Leucoindigo oxidised back to blue indigo in air",
        "Alizarin binding to the alum mordant",
    ]
    assert [step.said for step in player.steps] == [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9, 10, 11]]
    assert [(step.before, step.after, step.motion) for step in player.steps] == [
        (None, None, None),
        (None, None, None),
        ("var(--dye-leuco)", "var(--dye-indigo)", "oxidise"),
        (None, "var(--dye-madder-bright)", "dip"),
    ]
    first = player.steps[0]
    assert first.equation == "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2"
    assert [(one.formula, one.role) for one in first.species] == [
        ("Fe", "reactant"),
        ("CH3COOH", "reactant"),
        ("Fe(CH3COO)2", "product"),
        ("H2", "product"),
    ]
    assert isinstance(molecule, AskedMolecule)
    assert (molecule.title, molecule.formula, molecule.pubchem_cid, molecule.geometry) == (
        "Alizarin",
        "C14H8O4",
        ALIZARIN,
        None,
    )


def test_a_player_of_one_step_is_not_played_and_a_block_that_does_not_move_draws_no_figure() -> None:
    player = BLOCKS.validate_python(golden_json("explainer.phase-b.golden.json")["sections"][3]["blocks"][0])
    alone = player.model_copy(update={"steps": player.steps[:1]})
    assert figures([alone]) == []
    assert figures(blocks("explainer.phase-b.golden.json", "s3")) == []


def test_a_timeline_steps_through_each_year_with_its_places_and_sentences() -> None:
    (timeline,) = figures(blocks("explainer.phase-c.golden.json", "s4"))
    assert isinstance(timeline, AskedTimeline)
    assert [(stop.label, stop.year, stop.places, stop.said) for stop in timeline.stops] == [
        ("15th century", 1401, ["Fustat"], [0]),
        ("1586", 1586, ["Dhamadka", "Sindh", "Kutch"], [1, 3]),
        ("2001", 2001, ["Ajrakhpur"], [2]),
    ]
    (block,) = blocks("explainer.phase-c.golden.json", "s4")
    one = block.model_copy(update={"points": block.points[:1], "routes": []})
    assert figures([one]) == []


def test_a_stop_is_labelled_by_its_shortest_span_and_placed_by_its_first_year() -> None:
    (block,) = blocks("explainer.phase-c.golden.json", "s4")
    route = block.routes[0]
    assert (route.year_from, route.year_to) == (1586, 1631)
    alone = block.model_copy(update={"points": [p for p in block.points if p.year_from != 1586]})
    (timeline,) = figures([alone])
    assert [(stop.label, stop.year) for stop in timeline.stops] == [
        ("15th century", 1401),
        ("1586–1631", 1586),
        ("2001", 2001),
    ]


def test_a_kit_figure_with_a_motion_plays_its_panels_and_one_without_draws_none() -> None:
    vat, paste, section = blocks("explainer.kit-figure.golden.json", "s1")
    dips = figures([vat, paste, section])
    assert [figure.kind for figure in dips] == ["dips", "dips"]
    assert [(step.label, step.after, step.motion) for step in dips[0].steps] == [
        ("Green", "var(--dye-leuco)", "dip"),
        ("Blue", "var(--dye-indigo)", "take"),
    ]
    assert (dips[1].steps[0].before, dips[1].steps[0].after, dips[1].steps[0].motion) == (
        "var(--dye-lime)",
        "var(--dye-lime-edge)",
        "dry",
    )
    assert figures([section]) == []


def test_a_process_ladder_plays_its_stages_each_with_its_own_sentences() -> None:
    (stages,) = figures(blocks("explainer.document.golden.json", "s1")[:1])
    assert stages.kind == "stages"
    assert [step.said for step in stages.steps] == [[0, 1], [2, 3], [4], [5]]
    assert stages.steps[1].label == "Kut (iron-black printing)"


def test_the_colours_an_answer_paints_are_the_web_player_s_depicted_materials() -> None:
    web = WEB_FILLS.read_text(encoding="utf-8")
    for word, paint in COLOUR_SPECIMENS.items():
        assert f'  {word}: "{paint}"' in web


def test_the_figures_the_view_draws_are_the_shared_golden() -> None:
    cases = (
        ("explainer.phase-b.golden.json", "s4"),
        ("explainer.phase-c.golden.json", "s4"),
        ("explainer.kit-figure.golden.json", "s1"),
        ("explainer.document.golden.json", "s1"),
    )
    golden = golden_json(FIGURES_GOLDEN)["sections"]
    shape = TypeAdapter(list[AskedFigure])
    built = [shape.dump_python(figures(blocks(*case)), mode="json", by_alias=True) for case in cases]
    held = [[_unturned(figure) for figure in section["figures"]] for section in golden]
    assert built == held


def _unturned(figure: dict[str, Any]) -> dict[str, Any]:
    return {**figure, "geometry": None} if figure["kind"] == "molecule" else figure


class Reader:
    def __init__(self, sdf: str | None = SDF, failure: bool = False) -> None:
        self.sdf, self.failure, self.asked = sdf, failure, []

    async def conformer(self, cid: int) -> str | None:
        self.asked.append(cid)
        if self.failure:
            raise ExternalFailure("PubChem could not be reached")
        return self.sdf


def answer() -> AskedAnswer:
    golden = golden_json(FIGURES_GOLDEN)["sections"][0]
    section = AskedSection.model_validate(
        {**golden, "figures": [_unturned(figure) for figure in golden["figures"]]}
    )
    return AskedAnswer.model_construct(sections=[section])


def molecule_of(shown: AskedAnswer) -> AskedMolecule:
    return next(figure for figure in shown.sections[0].figures if isinstance(figure, AskedMolecule))


async def test_an_answer_s_molecule_carries_its_conformer_s_geometry_read_once() -> None:
    reader = Reader()

    async def opened() -> Reader:
        return reader

    shown = await drawn_molecules(answer(), opened)
    assert reader.asked == [ALIZARIN]
    geometry = molecule_of(shown).geometry
    assert geometry == conformer_geometry(SDF)
    assert len(geometry.atoms) == 26 and {atom[0] for atom in geometry.atoms} == {"C", "H", "O"}
    golden = golden_json(FIGURES_GOLDEN)["sections"][0]["figures"][1]["geometry"]
    assert json.loads(geometry.model_dump_json(by_alias=True)) == golden


@pytest.mark.parametrize(
    "reader",
    [Reader(failure=True), Reader(sdf=None), Reader(sdf=SDF.replace(" O ", " Se"))],
    ids=["unreachable", "no conformer", "an element the kit does not draw"],
)
async def test_a_molecule_whose_conformer_cannot_be_drawn_stays_a_named_figure(reader: Reader) -> None:
    async def opened() -> Reader:
        return reader

    shown = await drawn_molecules(answer(), opened)
    assert molecule_of(shown).geometry is None and molecule_of(shown).title == "Alizarin"


async def test_without_a_conformer_store_the_answer_keeps_its_figures_and_asks_nothing() -> None:
    async def missing() -> Reader:
        raise NotConfigured("media", "no bucket")

    before = answer()
    assert await drawn_molecules(before, missing) == before
    empty = AskedAnswer.model_construct(sections=[])

    async def never() -> Reader:
        raise AssertionError("no molecule, so no conformer is asked for")

    assert await drawn_molecules(empty, never) is empty


def test_the_golden_is_utf8_with_lf_endings() -> None:
    raw = (Path(REPO) / "shared" / FIGURES_GOLDEN).read_bytes()
    assert b"\r\n" not in raw and raw.decode("utf-8").endswith("\n")
