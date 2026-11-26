from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Annotated

from pydantic import Field

from app.core.errors import Refused
from app.research.base import ContractModel, absent, empty
from app.research.component_specs_general import (
    GENERAL_CHART,
    GENERAL_DRAWING,
    GENERAL_MAP_LAYER,
    GENERAL_TABLE,
    GENERAL_TIMELINE,
)
from app.research.component_specs_kit import KIT_DIAGRAM
from app.research.page_render import INTERACTIVE_KINDS
from app.research.page_report import PageReport
from app.research.page_report_rules import FAIL

from .mcp_guides import (
    BAR,
    CONTENTS_ADDRESS,
    GuideSheet,
    guide_sheet,
    guide_sheets,
    sheet_holding,
    sheet_matching,
)

__all__ = [
    "COOKBOOK",
    "DESIGN_READING",
    "KIND_RULES",
    "KIT_PARTS",
    "OPENING_PAGE",
    "PAGES_HANDED_MAX",
    "PICTURE_RULES",
    "PLAYBOOK",
    "STORYBOARD_SECTIONS",
    "UNITS",
    "GuideUnread",
    "HandedGuide",
    "ReadToken",
    "RulePage",
    "cookbook_entry",
    "design_read_token",
    "design_sheets",
    "failed_rules_guide",
    "handed",
    "kind_anchor",
    "kinds_guide",
    "opening_guide",
    "page_guide",
    "picture_guide",
    "refuse_unread",
    "rule_sheet",
    "storyboard_guide",
]

PAGES_HANDED_MAX = 2
PLAYBOOK = "playbook"
COOKBOOK = "cookbook"
CHECKLIST = "page-checklist"
COMPONENTS = "components"
KIT_CONTRACT = "component-specs-general"
INTERACTIVES = "kalavigyan-interactives"
STORYBOARD = "storyboard"
OPENING_PAGE = f"{PLAYBOOK}/1"
Anchor = tuple[str, str]
DESIGN_RULES: Anchor = (COMPONENTS, "The design rules for a contributed figure")
FIGURE_KIT: Anchor = (COMPONENTS, "The figure kit")
KIT_PARTS: Anchor = (KIT_CONTRACT, "The figure kit (decision 0199)")
DECLARED: Anchor = (COMPONENTS, "The declared kinds")
PLACES: Anchor = (COMPONENTS, "A map of places")
MATERIALS: Anchor = (COMPONENTS, "Depicted materials")
UNITS: Anchor = (COMPONENTS, "Units and citations")
PLAYERS: Anchor = (INTERACTIVES, "What a state may show")
FIGURE_KINDS = frozenset({GENERAL_DRAWING, KIT_DIAGRAM})
KIND_RULES: Mapping[str, Anchor] = MappingProxyType(
    {
        GENERAL_DRAWING: DESIGN_RULES,
        KIT_DIAGRAM: FIGURE_KIT,
        **dict.fromkeys((GENERAL_CHART, GENERAL_TABLE, GENERAL_TIMELINE, GENERAL_MAP_LAYER), DECLARED),
        "timeline_map": PLACES,
        **dict.fromkeys(("swatch_cards", "swatch_pair"), MATERIALS),
        **dict.fromkeys(sorted(INTERACTIVE_KINDS), PLAYERS),
    }
)
DESIGN_READING: tuple[Anchor, ...] = (DESIGN_RULES, FIGURE_KIT)
PICTURE_RULES = (2, 3, 7, 14)
STORYBOARD_SECTIONS: tuple[Anchor, ...] = (
    (STORYBOARD, "The rows"),
    (STORYBOARD, "A craft's own player, storyboarded from what the server composes"),
)
READ_TOKEN_PREFIX = "kvread-"
READ_TOKEN_DIGITS = 16
READ_TOKEN_MAX_CHARS = 64
UNREAD = "GUIDE_UNREAD"
HOW = f"Read any other page with get_page and guide set to its address; {CONTENTS_ADDRESS} lists every page."
READ_TOKEN_DESCRIPTION = (
    "The read_token returned with KalaVigyan's design pages; components added to a draft that holds none, "
    "and a bundle with components, are held back without it"
)
UNREAD_MESSAGE = (
    "Nothing was changed. Before a page's first components, read the design pages below, the design rules "
    "for a contributed figure and the figure kit; then send the same call again with read_token "
    '"{token}". Every component you build follows them.'
)

ReadToken = Annotated[str | None, Field(max_length=READ_TOKEN_MAX_CHARS, description=READ_TOKEN_DESCRIPTION)]


class RulePage(ContractModel):
    rule: int = Field(ge=1)
    page: str


class HandedGuide(ContractModel):
    pages: list[GuideSheet] = Field(min_length=1, max_length=PAGES_HANDED_MAX)
    next: str | None = None
    rules: list[RulePage] = Field(default_factory=list, exclude_if=empty)
    read_token: str | None = Field(default=None, exclude_if=absent)
    how: str = HOW


class GuideUnread(Refused):
    def __init__(self, guide: HandedGuide) -> None:
        said = UNREAD_MESSAGE.format(token=guide.read_token)
        super().__init__(UNREAD, "\n\n".join([said, *(sheet.served() for sheet in guide.pages)]))
        self.guide = guide


def handed(sheets: Iterable[GuideSheet], *, rules: Sequence[RulePage] = ()) -> HandedGuide:
    distinct = list({sheet.address: sheet for sheet in sheets}.values())
    shown = distinct[:PAGES_HANDED_MAX]
    held = {sheet.address for sheet in shown}
    following = [sheet.address for sheet in distinct[PAGES_HANDED_MAX:]]
    following += [sheet.next for sheet in shown if sheet.next is not None and sheet.next not in held]
    design = {sheet.address for sheet in design_sheets()}
    return HandedGuide(
        pages=shown,
        next=following[0] if following else None,
        rules=list(rules),
        read_token=design_read_token() if design <= held else None,
    )


def opening_guide() -> HandedGuide:
    return handed([guide_sheet(OPENING_PAGE), guide_sheets(BAR)[0]])


def page_guide(address: str) -> HandedGuide:
    design = design_sheets()
    if address in {sheet.address for sheet in design}:
        return handed(design)
    return handed([guide_sheet(address)])


def kinds_guide(kinds: Iterable[str]) -> HandedGuide | None:
    listed = list(dict.fromkeys(kinds))
    if not listed:
        return None
    sheets = [sheet_holding(*kind_anchor(kind)) for kind in listed]
    if any(kind in FIGURE_KINDS for kind in listed):
        sheets.append(sheet_holding(*KIT_PARTS))
    return handed(sheets)


def cookbook_entry(kind: str) -> Anchor:
    return (COOKBOOK, f"`{kind}`")


def kind_anchor(kind: str) -> Anchor:
    if kind in KIND_RULES:
        return KIND_RULES[kind]
    entry = cookbook_entry(kind)
    held = any(entry[1] in sheet.sections for sheet in guide_sheets(COOKBOOK))
    return entry if held else UNITS


def rule_sheet(number: int) -> GuideSheet:
    return sheet_matching(CHECKLIST, re.compile(rf"^{number}\. \*\*", re.MULTILINE))


def failed_rules_guide(report: PageReport | None) -> HandedGuide | None:
    failed = sorted({rule.rule for rule in report.rules if rule.verdict == FAIL}) if report else []
    return _ruled(failed) if failed else None


def picture_guide() -> HandedGuide:
    return _ruled(PICTURE_RULES)


def storyboard_guide() -> HandedGuide:
    return handed(sheet_holding(*anchor) for anchor in STORYBOARD_SECTIONS)


def design_sheets() -> list[GuideSheet]:
    found = (sheet_holding(*anchor) for anchor in DESIGN_READING)
    return list({sheet.address: sheet for sheet in found}.values())


def design_read_token() -> str:
    joined = "\n".join(f"{sheet.address}\n{sheet.text}" for sheet in design_sheets())
    return READ_TOKEN_PREFIX + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:READ_TOKEN_DIGITS]


def refuse_unread(token: str | None) -> None:
    if token == design_read_token():
        return
    raise GuideUnread(handed(design_sheets()))


def _ruled(numbers: Sequence[int]) -> HandedGuide:
    sheets = [rule_sheet(number) for number in numbers]
    pages = [RulePage(rule=number, page=sheet.address) for number, sheet in zip(numbers, sheets, strict=True)]
    return handed(sheets, rules=pages)
