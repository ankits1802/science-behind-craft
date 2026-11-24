from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.research.art_kit import VESSELS, parts_named_by
from app.research.blocks_kit import KIT_FIGURE_KIND, KitFigureBlock, KitLabel
from app.research.blocks_matter import StepColour
from app.research.citations import Citation
from app.research.colour_key import depicted_material
from app.research.component_specs_kit import DeclaredDiagramSpec
from app.research.unit_ids import UnitRange
from app.research.vocabulary import FACT_LEVELS
from app.schemas.science import CitedClaim, ProcessStageView

from .mechanisms import Concept
from .process_view import craft_process
from .reaction_colours import step_colours
from .records import ProcessRecords

__all__ = ["BATH_STAGES", "KIT_FIGURE_SUFFIX", "concept_kit_figure"]

KIT_FIGURE_SUFFIX = "kit"
BATH_STAGES = frozenset({"MORDANT", "DYE"})
RESIST_PREFIX = "resist:"
CLOTH_PART = "cloth"
CLOTH_FORM = "length"
BEFORE_AFTER = "before_after"
DYE_TOKEN = "--dye-{name}"
FIGURE_UNITS = UnitRange("answer figure", 1, 99)
WORDS = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class _Change:
    before: StepColour
    after: StepColour


@dataclass(frozen=True)
class _Vessel:
    word: str
    citations: tuple[Citation, ...]


@dataclass
class _Labels:
    shown: list[KitLabel] = field(default_factory=list)

    def unit(self, text: str, citations: Iterable[Citation] = ()) -> str:
        ref = FIGURE_UNITS.unit(len(self.shown))
        cited = list({citation.id: citation for citation in citations}.values())
        self.shown.append(KitLabel(ref=ref, text=text, citations=cited))
        return ref


def concept_kit_figure(concept: Concept, records: ProcessRecords, *, block_id: str) -> KitFigureBlock | None:
    stage = _concept_stage(concept, records)
    claims = _facts([*concept.claims, *(stage.claims if stage is not None else [])])
    change = _change(claims)
    if change is None:
        return None
    names = _substances(concept, stage)
    before = depicted_material(change.before.colour, names)
    after = depicted_material(change.after.colour, names)
    if before is None or after is None or before == after:
        return None
    tokens = (DYE_TOKEN.format(name=before), DYE_TOKEN.format(name=after))
    return _figure(block_id, change, tokens, _vessel(stage, claims))


def _concept_stage(concept: Concept, records: ProcessRecords) -> ProcessStageView | None:
    stages = [stage for process in craft_process(records).processes for stage in process.stages]
    if concept.key.startswith(RESIST_PREFIX):
        wanted = concept.key.removeprefix(RESIST_PREFIX)
        return next((stage for stage in stages if str(stage.id) == wanted), None)
    played = {reaction.id for reaction in concept.reactions}
    return next((stage for stage in stages if any(r.id in played for r in stage.reactions)), None)


def _facts(claims: Sequence[CitedClaim]) -> list[CitedClaim]:
    found = {claim.id: claim for claim in claims if claim.level in FACT_LEVELS}
    return list(found.values())


def _change(claims: Sequence[CitedClaim]) -> _Change | None:
    for claim in claims:
        if CLOTH_PART not in dict(parts_named_by(" ".join(_texts(claim)))):
            continue
        sides = {colour.side: colour for colour in step_colours(claim.citations)}
        before, after = sides.get("BEFORE"), sides.get("AFTER")
        if before is not None and after is not None and before.colour != after.colour:
            return _Change(before, after)
    return None


def _texts(claim: CitedClaim) -> list[str]:
    return [claim.text, *(citation.quote for citation in claim.citations if citation.quote)]


def _substances(concept: Concept, stage: ProcessStageView | None) -> list[str]:
    names = [material.name for material in stage.materials] if stage is not None else []
    names += [s.name for reaction in concept.reactions for s in reaction.species if s.name]
    return [*names, concept.label, *concept.words]


def _vessel(stage: ProcessStageView | None, claims: Sequence[CitedClaim]) -> _Vessel | None:
    if stage is None or stage.stage_type not in BATH_STAGES:
        return None
    for claim in claims:
        words = WORDS.findall(" ".join(_texts(claim)).casefold())
        found = next((word for word in words if word in VESSELS), None)
        if found is not None:
            return _Vessel(found, tuple(claim.citations))
    return None


def _figure(
    block_id: str, change: _Change, tokens: tuple[str, str], vessel: _Vessel | None
) -> KitFigureBlock:
    before, after = change.before.colour.casefold(), change.after.colour.casefold()
    labels = _Labels()
    where = f" in the {vessel.word}" if vessel is not None else ""
    head = {"title": labels.unit(f"{before.capitalize()} to {after}")}
    alt = labels.unit(f"Cloth drawn {before}{where}, then {after}")
    first = {"label": labels.unit(before.capitalize()), **_first_parts(change, tokens[0], vessel, labels)}
    second: dict[str, Any] = {"label": labels.unit(after.capitalize()), "motion": "take"}
    second["parts"] = [_cloth(tokens[1], labels.unit(f"Cloth, {after}", change.after.citations))]
    diagram = {"head": head, "layout": BEFORE_AFTER, "alt": alt, "panels": [first, second]}
    return KitFigureBlock(
        id=block_id,
        kind=KIT_FIGURE_KIND,
        version=1,
        reuse=None,
        diagram=DeclaredDiagramSpec.model_validate(diagram),
        labels=labels.shown,
    )


def _first_parts(change: _Change, token: str, vessel: _Vessel | None, labels: _Labels) -> dict[str, Any]:
    before = change.before.colour.casefold()
    if vessel is None:
        return {"parts": [_cloth(token, labels.unit(f"Cloth, {before}", change.before.citations))]}
    cited = [*vessel.citations, *change.before.citations]
    label = labels.unit(f"Cloth in the {vessel.word}", cited)
    return {
        "motion": "dip",
        "parts": [{"part": "bath", "vessel": vessel.word, "piece": token, "label": label}],
    }


def _cloth(token: str, label: str) -> dict[str, str]:
    return {"part": CLOTH_PART, "form": CLOTH_FORM, "material": token, "label": label}
