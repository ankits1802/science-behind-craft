from __future__ import annotations

import re
from collections.abc import Iterator, Sequence

from app.research.blocks_matter import StepColour
from app.research.citations import Citation
from app.research.colours import COLOUR_SURFACES, colour_of

__all__ = ["CHANGE_PATTERN", "DEVELOP_PATTERN", "after_phrase", "step_colours"]

COLOUR = rf"(?:[a-z]+-)*(?:{'|'.join(COLOUR_SURFACES)})"
MODIFIERS = r"(?:(?:bright|pale|deep|dark|light|rich|fast|dull|vivid)\s+){0,3}"
PACE = r"(?:(?:rapidly|slowly|quickly|gradually|soon)\s+)?"
CHANGE_VERBS = r"(?:becomes|become|turns|turn|turned|turning)"
DEVELOP_VERBS = r"(?:develops|develop|developed|developing|gives|produces|yields)"
CHANGE_PATTERN = re.compile(
    rf"\b(?:at first|first|initially)\s+{MODIFIERS}(?P<before>{COLOUR})\b[^.;:!?]*?"
    rf"\b{CHANGE_VERBS}\s+{PACE}{MODIFIERS}(?P<after>{COLOUR})\b",
    re.IGNORECASE,
)
DEVELOP_PATTERN = re.compile(
    rf"\b{DEVELOP_VERBS}\s+(?:(?:a|an|the)\s+)?{MODIFIERS}(?P<after>{COLOUR})\b",
    re.IGNORECASE,
)
AFTER_VERB = re.compile(rf"\b(?:{CHANGE_VERBS}|{DEVELOP_VERBS})\b", re.IGNORECASE)
NEGATIONS = re.compile(r"\b(?:not|never|no|without)\b|n't\b", re.IGNORECASE)
NEGATION_WINDOW = 24
STATED_MAX_CHARS = 200


def after_phrase(stated: str, limit: int) -> str | None:
    if len(stated) <= limit:
        return stated
    verbs = list(AFTER_VERB.finditer(stated))
    tail = stated[verbs[-1].start() :] if verbs else ""
    return tail if 0 < len(tail) <= limit else None


def step_colours(citations: Sequence[Citation]) -> list[StepColour]:
    found: dict[str, StepColour] = {}
    for citation in citations:
        for colour in _stated(citation):
            found.setdefault(colour.side, colour)
    return [found[side] for side in ("BEFORE", "AFTER") if side in found]


def _stated(citation: Citation) -> Iterator[StepColour]:
    quote = citation.quote or ""
    for match in CHANGE_PATTERN.finditer(quote):
        if not _negated(quote, match.start()):
            yield from _sides(match, citation, ("before", "after"))
    for match in DEVELOP_PATTERN.finditer(quote):
        if not _negated(quote, match.start()):
            yield from _sides(match, citation, ("after",))


def _sides(match: re.Match[str], citation: Citation, groups: Sequence[str]) -> Iterator[StepColour]:
    if len(match.group(0)) > STATED_MAX_CHARS:
        return
    for group in groups:
        colour = colour_of(match.group(group))
        if colour is not None:
            yield StepColour(side=group.upper(), colour=colour, stated=match.group(0), citations=[citation])


def _negated(quote: str, start: int) -> bool:
    return NEGATIONS.search(quote[max(0, start - NEGATION_WINDOW) : start]) is not None
