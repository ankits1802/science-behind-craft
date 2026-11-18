from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.research.blocks import ExplainerSentence, named_in, stated_texts
from app.research.blocks_signature import LOST_WAX_STEPS, SWATCHES_MAX
from app.research.quotes import quote_occurs
from app.science.records import CompoundRecord

from .signature_words import (
    AIR_CUE,
    BODY_WORDS,
    CHEMICAL_CUE,
    COLOUR_WORDS,
    CUED_MORDANTS,
    DIP_CONTEXT,
    DIP_COUNT,
    DYE_WORDS,
    FERMENTED_CUE,
    FIBRE_WORDS,
    FIRING_CONTEXT,
    INSOLUBLE,
    KETO_COLOURS,
    KETO_COMPOUNDS,
    KETO_NAMES,
    LEUCO_COLOURS,
    LEUCO_COMPOUNDS,
    LEUCO_NAMES,
    LOST_WAX_CUES,
    METAL_WORDS,
    MORDANT_COLOURS,
    MORDANT_WORDS,
    NEGATION,
    NO_MORDANT,
    OXIDISING_CUE,
    REDUCING_CUE,
    SHADE_WORDS,
    SOLUBLE,
    TEMPERATURE,
    VAT_CONTENTS,
    first_named,
    named_once,
    names_any,
    names_first,
    says,
)

__all__ = ["MIN_LOST_WAX_STEPS", "MIN_SWATCHES", "FigureEvidence", "figure_fields"]

MIN_SWATCHES = 2
MIN_LOST_WAX_STEPS = 2
VAT_SUBJECTS = ("indigo", "vat", "naand", "maat")
TANNIN_WORDS = ("mordant", "tannin", "tannic")
NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight")

Fields = dict[str, Any]


@dataclass(frozen=True)
class FigureEvidence:
    facts: tuple[ExplainerSentence, ...]
    compounds: tuple[CompoundRecord, ...] = ()
    record_sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class _Form:
    form: str
    names: tuple[str, ...]
    colours: tuple[str, ...]
    solubility: re.Pattern[str]
    soluble: bool
    compounds: tuple[str, ...]


FORMS = (
    _Form("KETO", KETO_NAMES, KETO_COLOURS, INSOLUBLE, False, KETO_COMPOUNDS),
    _Form("LEUCO", LEUCO_NAMES, LEUCO_COLOURS, SOLUBLE, True, LEUCO_COMPOUNDS),
)


def figure_fields(kind: str, evidence: FigureEvidence) -> Fields | None:
    return BUILDERS[kind](evidence)


def _mordant_bath(evidence: FigureEvidence) -> Fields | None:
    mordanted = _mordanted(evidence.facts)
    dye = first_named([swatch["sentence"] for swatch in mordanted], DYE_WORDS)
    if dye is None:
        return None
    plain = next((s for s in (_plain_swatch(fact, dye) for fact in evidence.facts) if s is not None), None)
    swatches = ([plain] if plain is not None else []) + mordanted
    fibre = names_first([swatch["sentence"] for swatch in swatches], FIBRE_WORDS)
    if len(swatches) < MIN_SWATCHES or fibre is None:
        return None
    return {"dye": dye, "fibre": fibre, "swatches": swatches[:SWATCHES_MAX]}


def _mordanted(facts: Sequence[ExplainerSentence]) -> list[Fields]:
    ordered = sorted(facts, key=lambda s: (not _says_itself(s, DYE_WORDS), not _says_itself(s, TANNIN_WORDS)))
    chosen: dict[str, Fields] = {}
    for sentence in ordered:
        swatch = _mordant_swatch(sentence)
        if swatch is not None:
            chosen.setdefault(swatch["mordant"], swatch)
    return [chosen[mordant] for mordant in MORDANT_WORDS if mordant in chosen]


def _mordant_swatch(sentence: ExplainerSentence) -> Fields | None:
    text = _own_text(sentence)
    mordant = named_once(sentence, MORDANT_WORDS)
    colour = named_once(sentence, MORDANT_COLOURS)
    if mordant is None or colour is None or NEGATION.search(text) or NO_MORDANT.search(text):
        return None
    if mordant in CUED_MORDANTS and not named_in("mordant", sentence):
        return None
    return {"mordant": mordant, "colour": colour, "sentence": sentence}


def _plain_swatch(sentence: ExplainerSentence, dye: str) -> Fields | None:
    colour = named_once(sentence, COLOUR_WORDS)
    if colour is None or not NO_MORDANT.search(_own_text(sentence)) or not named_in(dye, sentence):
        return None
    if names_any(sentence, MORDANT_WORDS):
        return None
    return {"mordant": None, "colour": colour, "sentence": sentence}


def _indigo_vat(evidence: FigureEvidence) -> Fields | None:
    facts = evidence.facts
    forms = [form for form in (_form(spec, evidence) for spec in FORMS) if form is not None]
    used = {form["sentence"].id for form in forms}
    lift = _lift([fact for fact in facts if fact.id not in used])
    vat = _vat_kind(facts)
    if lift is None or vat is None or not forms:
        return None
    return {"vat": vat, "lift": lift, "forms": forms, "dips": _dips(facts), "contents": _contents(facts, vat)}


def _form(spec: _Form, evidence: FigureEvidence) -> Fields | None:
    for sentence in evidence.facts:
        name = _first(sentence, spec.names)
        colour = _first(sentence, spec.colours)
        if name and colour and says(sentence, spec.solubility):
            return {
                "form": spec.form,
                "name": name,
                "colour": colour,
                "soluble": spec.soluble,
                "compound": _compound(spec.compounds, evidence),
                "sentence": sentence,
            }
    return None


def _compound(names: Sequence[str], evidence: FigureEvidence) -> Fields | None:
    for compound in evidence.compounds:
        source_id = str(compound.source_id) if compound.source_id else None
        if compound.name.casefold() not in names or compound.pubchem_cid is None:
            continue
        if source_id is not None and source_id in evidence.record_sources:
            return {
                "compoundId": str(compound.id),
                "pubchemCid": compound.pubchem_cid,
                "formula": compound.formula,
                "sourceId": source_id,
            }
    return None


def _lift(facts: Sequence[ExplainerSentence]) -> ExplainerSentence | None:
    lifted = [fact for fact in facts if named_in("blue", fact) and says(fact, AIR_CUE)]
    return next((fact for fact in lifted if named_in("green", fact)), lifted[0] if lifted else None)


def _vat_kind(facts: Sequence[ExplainerSentence]) -> str | None:
    told = [
        (says(fact, FERMENTED_CUE), says(fact, CHEMICAL_CUE))
        for fact in facts
        if names_any(fact, VAT_SUBJECTS)
    ]
    for fermented, chemical in told:
        if fermented != chemical:
            return "FERMENTED" if fermented else "CHEMICAL"
    return "FERMENTED" if any(fermented for fermented, _ in told) else None


def _contents(facts: Sequence[ExplainerSentence], vat: str) -> list[Fields]:
    cue = FERMENTED_CUE if vat == "FERMENTED" else CHEMICAL_CUE
    told = [fact for fact in facts if names_any(fact, VAT_SUBJECTS) and says(fact, cue)]
    contents: list[Fields] = []
    for group in VAT_CONTENTS[vat]:
        found = next(((fact, name) for fact in told if (name := _first(fact, group))), None)
        if found is not None:
            contents.append({"name": found[1], "sentence": found[0]})
    return contents


def _dips(facts: Sequence[ExplainerSentence]) -> list[Fields]:
    found: dict[int, Fields] = {}
    for fact in facts:
        stated = _dip_count(fact) if says(fact, DIP_CONTEXT) else None
        if stated is not None and stated[0] not in found:
            found[stated[0]] = {
                "dips": stated[0],
                "stated": stated[1],
                "shade": _first(fact, SHADE_WORDS),
                "sentence": fact,
            }
    return [found[count] for count in sorted(found)]


def _dip_count(sentence: ExplainerSentence) -> tuple[int, str] | None:
    for text in stated_texts(sentence):
        match = DIP_COUNT.search(text)
        if match is not None:
            word = match.group(1).casefold()
            return (int(word) if word.isdigit() else NUMBER_WORDS.index(word) + 1), match.group(0)
    return None


def _lost_wax(evidence: FigureEvidence) -> Fields | None:
    steps: list[Fields] = []
    used: set[str] = set()
    for step in LOST_WAX_STEPS:
        found = _step_fact(step, [fact for fact in evidence.facts if fact.id not in used])
        if found is not None:
            used.add(found.id)
            steps.append({"step": step, "sentence": found})
    metal = first_named([step["sentence"] for step in steps], METAL_WORDS)
    if len(steps) < MIN_LOST_WAX_STEPS or metal is None:
        return None
    return {"metal": metal, "steps": steps}


def _step_fact(step: str, facts: Sequence[ExplainerSentence]) -> ExplainerSentence | None:
    told = [fact for fact in facts if _tells_step(fact, step)]
    only = [
        fact
        for fact in told
        if not any(_tells_step(fact, other) for other in LOST_WAX_STEPS if other != step)
    ]
    return (only or told or [None])[0]


def _tells_step(sentence: ExplainerSentence, step: str) -> bool:
    return all(says(sentence, cue) for cue in LOST_WAX_CUES[step])


def _firing(evidence: FigureEvidence) -> Fields | None:
    facts = [fact for fact in evidence.facts if says(fact, FIRING_CONTEXT)]
    atmospheres = [found for found in (_atmosphere(name, facts) for name in ATMOSPHERES) if found]
    temperature = next(
        (
            {"stated": match.group(0), "sentence": fact}
            for fact in facts
            if (match := TEMPERATURE.search(fact.text))
        ),
        None,
    )
    sentences = [*(a["sentence"] for a in atmospheres), *([temperature["sentence"]] if temperature else [])]
    body = first_named(sentences, BODY_WORDS)
    if not atmospheres or body is None:
        return None
    return {"body": body, "atmospheres": atmospheres, "temperature": temperature}


def _atmosphere(name: str, facts: Sequence[ExplainerSentence]) -> Fields | None:
    cue, other = ATMOSPHERES[name]
    for fact in facts:
        colour = named_once(fact, COLOUR_WORDS)
        if colour is not None and says(fact, cue) and not says(fact, other):
            return {"atmosphere": name, "colour": colour, "sentence": fact}
    return None


def _first(sentence: ExplainerSentence, words: Sequence[str]) -> str | None:
    return next((word for word in words if named_in(word, sentence)), None)


def _says_itself(sentence: ExplainerSentence, words: Sequence[str]) -> bool:
    return any(quote_occurs(word, sentence.original or sentence.text) for word in words)


def _own_text(sentence: ExplainerSentence) -> str:
    return (sentence.original or sentence.text).casefold()


ATMOSPHERES: Mapping[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
    "OXIDISING": (OXIDISING_CUE, REDUCING_CUE),
    "REDUCING": (REDUCING_CUE, OXIDISING_CUE),
}
BUILDERS: Mapping[str, Callable[[FigureEvidence], Fields | None]] = {
    "indigo_vat": _indigo_vat,
    "mordant_bath": _mordant_bath,
    "lost_wax": _lost_wax,
    "firing": _firing,
}
