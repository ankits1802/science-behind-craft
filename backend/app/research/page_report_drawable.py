from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Protocol

from .base import ContractModel
from .coverage_chapters import field_chapter
from .monograph_page import MonographContent
from .stated_figures import quantities_in
from .timeline import years_stated

__all__ = [
    "DRAWABLE_RULE",
    "DRAWN_BY",
    "SHOWS",
    "HeldChange",
    "HeldShapes",
    "Opportunity",
    "drawable_evidence",
    "opportunities",
]

DRAWABLE_RULE = 29
REACTION, STAGES, PLACES_AND_DATES, QUANTITIES = SHOWS = (
    "REACTION",
    "STAGES",
    "PLACES_AND_DATES",
    "QUANTITIES",
)
PICTURE_KIND = "picture_plate"
PLACE_FIELD = "GEOGRAPHY"
CHANGE_FIELD, MAKING_FIELD, DATED_FIELD = "CHEMISTRY", "PROCESS", "HISTORY"
STAGES_MIN = 2
DATED_MIN = 2
QUANTITIES_MIN = 2
NAMES_MAX = 4
FACTS_MAX = 6
DRAWN_BY: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        REACTION: frozenset(
            {"reaction_player", "equation_card", "drawing", "diagram", "structure_diagram", "model_explainer"}
        ),
        STAGES: frozenset({"stage_player", "dip_player", "process_replay", "drawing", "diagram"}),
        PLACES_AND_DATES: frozenset({"timeline_map", "map_sequence"}),
        QUANTITIES: frozenset({"chart", "fact_table", "stat_tiles", "drawing", "diagram"}),
    }
)
WRITTEN: Mapping[str, str] = MappingProxyType(
    {
        REACTION: "a reaction_player or equation_card you write, its scenes drawn from the figure kit",
        STAGES: "a stage_player you write, each stage a kit scene of what its facts name",
        PLACES_AND_DATES: "a timeline_map declared from the places and dates, played through them",
        QUANTITIES: "a chart or fact_table declared from the facts that state them, drawn to scale",
    }
)
SHORTCUTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        REACTION: ("reaction_player",),
        STAGES: ("stage_player", "dip_player"),
        PLACES_AND_DATES: ("timeline_map",),
    }
)
SHORTCUT = "compose_component with kind {kind}, as a shortcut"
MEASURED = "{count} quantities with units stated in {field} with no figure of that field"
LINE = "{chapter}: {what}, stated by {facts}; draw it as {ways} if it serves the reader"
NOTHING_WAITS = "nothing this craft's facts state waits for a figure the page does not draw"


class StatedSentence(Protocol):
    @property
    def text(self) -> str: ...

    @property
    def field(self) -> str | None: ...

    @property
    def claim_ids(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class HeldChange:
    key: str
    said: str
    claims: tuple[str, ...]


@dataclass(frozen=True)
class HeldShapes:
    reactions: tuple[HeldChange, ...] = ()
    stages: tuple[HeldChange, ...] = ()
    composers: tuple[str, ...] = ()


class Opportunity(ContractModel):
    shows: Literal[*SHOWS]
    chapter: str
    what: str
    facts: list[str]
    ways: list[str]

    def line(self) -> str:
        return LINE.format(
            chapter=self.chapter, what=self.what, facts=", ".join(self.facts), ways=" or ".join(self.ways)
        )


@dataclass(frozen=True)
class _Figure:
    kind: str
    field: str
    claims: frozenset[str]


def opportunities(
    content: MonographContent, sentences: Sequence[StatedSentence], held: HeldShapes | None
) -> list[Opportunity]:
    figures = _figures(content)
    found = [*_reactions(held, figures), *_stages(held, figures)] if held is not None else []
    return [*found, *_places_and_dates(sentences, figures, held), *_quantities(sentences, figures, held)]


def drawable_evidence(found: Sequence[Opportunity]) -> tuple[bool, list[str]]:
    if not found:
        return True, [NOTHING_WAITS]
    return False, [opportunity.line() for opportunity in found]


def _figures(content: MonographContent) -> list[_Figure]:
    within: dict[str, set[str]] = defaultdict(set)
    for entry in content.layout:
        unit = content.units.get(entry.ref) if entry.within is not None else None
        if unit is not None and entry.within is not None:
            within[entry.within].update(unit.claim_ids)
    return [
        _Figure(c.kind, c.field, frozenset(within[c.label]))
        for c in content.components
        if c.kind != PICTURE_KIND
    ]


def _drawn(shows: str, figures: Sequence[_Figure], claims: Sequence[str]) -> bool:
    wanted = set(claims)
    return any(f.kind in DRAWN_BY[shows] and f.claims & wanted for f in figures)


def _opportunity(
    shows: str, field: str, what: str, claims: Sequence[str], held: HeldShapes | None
) -> Opportunity:
    composers = held.composers if held is not None else ()
    ways = [WRITTEN[shows], *(SHORTCUT.format(kind=k) for k in SHORTCUTS.get(shows, ()) if k in composers)]
    return Opportunity(
        shows=shows, chapter=field_chapter(field), what=what, facts=list(claims)[:FACTS_MAX], ways=ways
    )


def _reactions(held: HeldShapes, figures: Sequence[_Figure]) -> list[Opportunity]:
    return [
        _opportunity(
            REACTION,
            CHANGE_FIELD,
            f"the reaction {r.key}, {r.said}, balanced and drawn nowhere",
            r.claims,
            held,
        )
        for r in held.reactions
        if not _drawn(REACTION, figures, r.claims)
    ]


def _stages(held: HeldShapes, figures: Sequence[_Figure]) -> list[Opportunity]:
    claims = [claim for stage in held.stages for claim in stage.claims]
    if len(held.stages) < STAGES_MIN or _drawn(STAGES, figures, claims):
        return []
    names = ", ".join(stage.said for stage in held.stages[:NAMES_MAX])
    what = f"{len(held.stages)} stages in order ({names}) with no player stepping through them"
    return [_opportunity(STAGES, MAKING_FIELD, what, list(dict.fromkeys(claims)), held)]


def _places_and_dates(
    sentences: Sequence[StatedSentence], figures: Sequence[_Figure], held: HeldShapes | None
) -> list[Opportunity]:
    dated = [s for s in sentences if years_stated([s.text])]
    placed = [s for s in sentences if s.field == PLACE_FIELD]
    if len(dated) < DATED_MIN or not placed or any(f.kind in DRAWN_BY[PLACES_AND_DATES] for f in figures):
        return []
    what = f"{len(dated)} dated sentences and {len(placed)} of places with no map that moves through them"
    return [_opportunity(PLACES_AND_DATES, DATED_FIELD, what, _claims(dated), held)]


def _quantities(
    sentences: Sequence[StatedSentence], figures: Sequence[_Figure], held: HeldShapes | None
) -> list[Opportunity]:
    measured: dict[str, list[StatedSentence]] = defaultdict(list)
    for sentence in sentences:
        if sentence.field and any(q.unit for q in quantities_in(sentence.text)):
            measured[sentence.field].append(sentence)
    drawn = {f.field for f in figures if f.kind in DRAWN_BY[QUANTITIES]}
    return [
        _opportunity(
            QUANTITIES, name, MEASURED.format(count=len(stated), field=name.lower()), _claims(stated), held
        )
        for name, stated in measured.items()
        if len(stated) >= QUANTITIES_MIN and name not in drawn
    ]


def _claims(sentences: Sequence[StatedSentence]) -> list[str]:
    return list(dict.fromkeys(claim for sentence in sentences for claim in sentence.claim_ids))
