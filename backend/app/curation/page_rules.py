from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from app.research.chapter_keys import PLACED_ONCE_PER_CHAPTER, PLACED_ONCE_PER_PAGE
from app.research.colours import colour_of
from app.research.quotes import content_stem, content_words, normalise_quote_text

from .dossier import Dossier
from .entities import After, Stage
from .matching import stated_in
from .parts import Claim
from .problems import Problem
from .records import NativeName
from .vocabulary import WHY_DISCIPLINES

__all__ = [
    "LANGUAGE_LABEL",
    "NAMING_WORDS",
    "claim_of_stage",
    "names_the_craft",
    "native_name_problems",
    "placement_problems",
    "stage_page_problems",
    "states_colour_word",
]

NAMING_WORDS = re.compile(
    r"\b(?:called|call|calls|known\s+as|named|name|names|termed|spelt|spelled|referred\s+to\s+as)\b",
    re.IGNORECASE,
)
LANGUAGE_LABEL = re.compile(r"\b[A-Z][a-z]+:\s*$")
COLOUR_TERM = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
CRAFT_SUBJECT = "CRAFT"
STAGE_SUBJECT = "STAGE"
MATERIAL_SUBJECT = "MATERIAL"


def stage_page_problems(dossier: Dossier) -> list[Problem]:
    found = []
    for stage in dossier.stages:
        if stage.after is not None:
            found += [
                Problem(f"{stage.id}.after", text) for text in _after_messages(dossier, stage, stage.after)
            ]
        if stage.why_claim_id is not None:
            claim = dossier.claim(stage.why_claim_id)
            found += [
                Problem(f"{stage.id}.whyClaimId", text) for text in _why_messages(dossier, stage, claim)
            ]
    return found


def placement_problems(dossier: Dossier) -> list[Problem]:
    by_page: dict[str, list[str]] = defaultdict(list)
    by_chapter: dict[tuple[str, str], list[str]] = defaultdict(list)
    found = []
    for picture in dossier.pictures:
        placement = picture.placement
        if placement is None:
            continue
        by_page[placement.role].append(picture.id)
        by_chapter[(placement.chapter, placement.role)].append(picture.id)
        if placement.stage_id is not None and picture.stage_id not in (None, placement.stage_id):
            found.append(
                Problem(
                    f"{picture.id}.placement",
                    f"is placed at stage {placement.stage_id} but shows stage {picture.stage_id}",
                )
            )
    found += [
        Problem("pictures", f"{', '.join(ids)} are all placed {role}; a dossier places one")
        for role, ids in by_page.items()
        if role in PLACED_ONCE_PER_PAGE and len(ids) > 1
    ]
    found += [
        Problem("pictures", f"{', '.join(ids)} are all placed {role} in {chapter}; a chapter has one")
        for (chapter, role), ids in by_chapter.items()
        if role in PLACED_ONCE_PER_CHAPTER and len(ids) > 1
    ]
    return found


def native_name_problems(dossier: Dossier) -> list[Problem]:
    found = []
    for index, name in enumerate(dossier.native_names):
        claim = dossier.claim(name.claim_id)
        found += [Problem(f"nativeNames.{index}", text) for text in _native_name_messages(claim, name)]
    return found


def claim_of_stage(stage: Stage, claim: Claim) -> bool:
    return claim.id in stage.claim_ids or (
        claim.subject.type == STAGE_SUBJECT and claim.subject.ref == stage.id
    )


def states_colour_word(text: str, colour: str) -> bool:
    return any(
        colour_of(term) == colour for term in COLOUR_TERM.findall(normalise_quote_text(text).casefold())
    )


def names_the_craft(quote: str, name: str) -> bool:
    text = normalise_quote_text(quote)
    if NAMING_WORDS.search(text):
        return True
    at = text.casefold().find(normalise_quote_text(name).casefold())
    return at > 0 and LANGUAGE_LABEL.search(text[:at].rstrip(" (")) is not None


def _after_messages(dossier: Dossier, stage: Stage, after: After) -> list[str]:
    claim = dossier.claim(after.claim_id)
    if not claim_of_stage(stage, claim):
        return [f"{claim.id} is not a claim of {stage.id}; the after text rests on a fact claim of its stage"]
    quotes = [quote.quote for quote in claim.quotes]
    stated = {content_stem(word) for text in (claim.text, *quotes) for word in content_words(text)}
    missing = [word for word in dict.fromkeys(content_words(after.text)) if content_stem(word) not in stated]
    messages = (
        [f"{', '.join(missing)} in the after text is in neither {claim.id}'s text nor its quotes"]
        if missing
        else []
    )
    return messages + [
        f"the colour {colour} is named in none of {claim.id}'s quotes"
        for colour in after.colours
        if not any(states_colour_word(quote, colour) for quote in quotes)
    ]


def _why_messages(dossier: Dossier, stage: Stage, claim: Claim) -> list[str]:
    messages = []
    if claim.discipline not in WHY_DISCIPLINES:
        allowed = f"{', '.join(WHY_DISCIPLINES[:-1])} or {WHY_DISCIPLINES[-1]}"
        messages.append(f"{claim.id} is filed under {claim.discipline}; a why is filed under {allowed}")
    if not (claim_of_stage(stage, claim) or _about_its_materials(dossier, stage, claim)):
        messages.append(f"{claim.id} is about neither {stage.id} nor one of its materials")
    return messages


def _about_its_materials(dossier: Dossier, stage: Stage, claim: Claim) -> bool:
    used = {use.material_id for use in stage.materials}
    if claim.subject.type == MATERIAL_SUBJECT and claim.subject.ref in used:
        return True
    return any(claim.id in material.claim_ids for material in dossier.materials if material.id in used)


def _native_name_messages(claim: Claim, name: NativeName) -> list[str]:
    if claim.subject.type != CRAFT_SUBJECT:
        return [f"{claim.id} is about a {claim.subject.type}; a native name rests on a claim about the craft"]
    holding = _quotes_holding(name.text, (quote.quote for quote in claim.quotes))
    if not holding:
        return [f"{name.text!r} occurs in none of {claim.id}'s quotes"]
    if not any(names_the_craft(quote, name.text) for quote in holding):
        return [
            f"no quote of {claim.id} holding {name.text!r} says the craft is called that "
            "(called, known as, named, spelt, or a language label before the name)"
        ]
    return []


def _quotes_holding(text: str, quotes: Iterable[str]) -> list[str]:
    return [quote for quote in quotes if stated_in(text, [quote])]
