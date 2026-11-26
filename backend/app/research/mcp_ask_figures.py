from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Annotated, Literal

from pydantic import Field

from .base import ContractModel
from .blocks import BlockBase, ExplainerSentence, LadderStage, ProcessLadderBlock
from .blocks_journey import TimelineMapBlock
from .blocks_kit import KitFigureBlock
from .blocks_matter import Molecule3dBlock, ReactionPlayerBlock, ReactionStep
from .component_specs_kit import KitPanel
from .component_specs_science_geometry import MoleculeGeometry

__all__ = [
    "COLOUR_SPECIMENS",
    "AskedFigure",
    "AskedMolecule",
    "AskedPlayer",
    "AskedSpecies",
    "AskedStep",
    "AskedStop",
    "AskedTimeline",
    "section_figures",
]

COLOUR_SPECIMENS: Mapping[str, str] = {
    "RED": "var(--dye-madder-bright)",
    "BLUE": "var(--dye-indigo)",
    "BLACK": "var(--dye-kut)",
    "WHITE": "var(--dye-cloth)",
    "GREEN": "var(--dye-leuco)",
    "YELLOW": "var(--dye-harda)",
    "BROWN": "var(--dye-mud)",
    "GREY": "var(--dye-lime-edge)",
    "PINK": "var(--dye-pink)",
    "PURPLE": "color-mix(in srgb, var(--dye-madder) 55%, var(--dye-indigo))",
    "ORANGE": "var(--dye-kesari)",
    "MAROON": "var(--dye-madder)",
}
REACTIONS_TITLE = "The reactions, step by step"
STAGES_TITLE = "The stages, one after another"
STEPS_MIN = 2
STOPS_MIN = 2
BCE = "{year} BCE"
SPAN = "{start}–{end}"

FigureMotion = Literal["dip", "take", "dry", "react", "oxidise"]
OXIDISED = ("GREEN", "BLUE")


class AskedSpecies(ContractModel):
    name: str
    formula: str | None
    role: Literal["reactant", "product"]


class AskedStep(ContractModel):
    label: str
    note: str | None
    equation: str | None
    species: list[AskedSpecies]
    before: str | None
    after: str | None
    motion: FigureMotion | None
    said: list[int]


class AskedPlayer(ContractModel):
    kind: Literal["reaction", "stages", "dips"]
    title: str
    steps: list[AskedStep] = Field(min_length=STEPS_MIN)


class AskedStop(ContractModel):
    label: str
    places: list[str]
    said: list[int]


class AskedTimeline(ContractModel):
    kind: Literal["timeline"]
    title: str
    stops: list[AskedStop] = Field(min_length=STOPS_MIN)


class AskedMolecule(ContractModel):
    kind: Literal["molecule"]
    title: str
    formula: str | None
    pubchem_cid: int
    geometry: MoleculeGeometry | None = None


AskedFigure = Annotated[AskedPlayer | AskedTimeline | AskedMolecule, Field(discriminator="kind")]


def section_figures(blocks: Iterable[BlockBase], said: Mapping[str, int]) -> list[AskedFigure]:
    figures: list[AskedFigure] = []
    for block in blocks:
        figure = _figure(block, said)
        if figure is not None:
            figures.append(figure)
    return figures


def _figure(block: BlockBase, said: Mapping[str, int]) -> AskedFigure | None:
    if isinstance(block, ReactionPlayerBlock):
        return _player(
            "reaction", REACTIONS_TITLE, [_reaction_step(block, step, said) for step in block.steps]
        )
    if isinstance(block, ProcessLadderBlock):
        return _player("stages", STAGES_TITLE, [_stage_step(stage, said) for stage in block.stages])
    if isinstance(block, KitFigureBlock):
        return _dips(block)
    if isinstance(block, TimelineMapBlock):
        return _timeline(block, said)
    if isinstance(block, Molecule3dBlock):
        return AskedMolecule(
            kind="molecule", title=block.name, formula=block.formula, pubchem_cid=block.pubchem_cid
        )
    return None


def _player(
    kind: Literal["reaction", "stages", "dips"], title: str, steps: Sequence[AskedStep]
) -> AskedPlayer | None:
    if len(steps) < STEPS_MIN:
        return None
    return AskedPlayer(kind=kind, title=title, steps=list(steps))


def _indices(sentences: Iterable[ExplainerSentence], said: Mapping[str, int]) -> list[int]:
    return sorted({said[sentence.id] for sentence in sentences if sentence.id in said})


def _reaction_step(block: ReactionPlayerBlock, step: ReactionStep, said: Mapping[str, int]) -> AskedStep:
    words = {colour.side: colour.colour for colour in step.colours}
    colours = {side: COLOUR_SPECIMENS[word] for side, word in words.items()}
    notes = (note.sentence for note in block.notes if note.reaction_id == step.reaction_id)
    return AskedStep(
        label=step.label,
        note=step.stage,
        equation=step.equation,
        species=[
            AskedSpecies(
                name=species.name or species.formula or "", formula=species.formula, role=species.role.lower()
            )
            for species in step.species
        ],
        before=colours.get("BEFORE"),
        after=colours.get("AFTER"),
        motion=_change(words.get("BEFORE"), words.get("AFTER")),
        said=_indices(notes, said),
    )


def _stage_step(stage: LadderStage, said: Mapping[str, int]) -> AskedStep:
    after = stage.after.colours[0] if stage.after is not None and stage.after.colours else None
    return AskedStep(
        label=stage.name,
        note=stage.local_name,
        equation=None,
        species=[],
        before=None,
        after=COLOUR_SPECIMENS[after] if after is not None else None,
        motion=_change(None, after),
        said=_indices(stage.added_sentences(), said),
    )


def _change(before: str | None, after: str | None) -> FigureMotion | None:
    if after is None:
        return None
    return "oxidise" if (before, after) == OXIDISED else "dip"


def _dips(block: KitFigureBlock) -> AskedPlayer | None:
    if all(panel.motion is None for panel in block.diagram.panels):
        return None
    texts = {label.ref: label.text for label in block.labels}
    title = texts.get(block.diagram.head.title, "")
    return _player("dips", title, [_panel_step(panel, texts) for panel in block.diagram.panels])


def _panel_step(panel: KitPanel, texts: Mapping[str, str]) -> AskedStep:
    before, after = _panel_paints(panel)
    return AskedStep(
        label=texts.get(panel.label, ""),
        note=texts.get(panel.text) if panel.text is not None else None,
        equation=None,
        species=[],
        before=before,
        after=after,
        motion=panel.motion,
        said=[],
    )


def _panel_paints(panel: KitPanel) -> tuple[str | None, str | None]:
    for part in panel.parts:
        dried = getattr(part, "dried", None)
        material = (
            getattr(part, "material", None) or getattr(part, "piece", None) or getattr(part, "liquor", None)
        )
        if isinstance(material, str) and material.startswith("--"):
            return (_paint(material), _paint(dried)) if dried else (None, _paint(material))
    return None, None


def _paint(token: str) -> str:
    return f"var({token})"


def _timeline(block: TimelineMapBlock, said: Mapping[str, int]) -> AskedTimeline | None:
    stops = list(_stops(block, said))
    if len(stops) < STOPS_MIN:
        return None
    return AskedTimeline(kind="timeline", title="Through time", stops=stops)


def _stops(block: TimelineMapBlock, said: Mapping[str, int]) -> Iterator[AskedStop]:
    dated = [(point.year_from, point.year_to, [point.place], point.sentence) for point in block.points]
    dated += [
        (route.year_from, route.year_to, [route.start, route.end], route.sentence) for route in block.routes
    ]
    for year in sorted({start for start, _, _, _ in dated}):
        held = [entry for entry in dated if entry[0] == year]
        names = dict.fromkeys(block.places[place].name for _, _, places, _ in held for place in places)
        yield AskedStop(
            label=_years(year, held[0][1]),
            places=list(names),
            said=_indices((sentence for _, _, _, sentence in held), said),
        )


def _years(start: int, end: int) -> str:
    first, last = _year(start), _year(end)
    return first if start == end else SPAN.format(start=first, end=last)


def _year(year: int) -> str:
    return BCE.format(year=-year) if year < 0 else str(year)
