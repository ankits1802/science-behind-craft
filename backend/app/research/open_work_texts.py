from __future__ import annotations

from dataclasses import dataclass

from .open_work import (
    COMPONENT_NEED_TITLES,
    NO_ITEMS,
    REVIEW_QUEUE_LABELS,
    FieldStanding,
    Items,
    QueueStanding,
    SubjectStanding,
)
from .sections import DISCIPLINE_FIELDS

__all__ = [
    "REVIEW_ACCEPTANCE",
    "Wording",
    "component_wording",
    "counted",
    "dead_wording",
    "differ_wording",
    "field_wording",
    "page_form_wording",
    "page_layout_wording",
    "review_needed",
    "second_source_wording",
    "unarchived_wording",
    "upgrade_wording",
]

REVIEW_ACCEPTANCE = (
    "Each one approved or rejected in admin settings, with the reason kept for a rejection; a reviewer's "
    "own proposal is approved at once and never waits here."
)
SECOND_SOURCE_ACCEPTANCE = (
    "A second quote for each fact from a different publisher, verbatim with its locator, proposed on the "
    "same fact; a near-verbatim rewrite of the first source is not independent support."
)
DIFFER_ACCEPTANCE = (
    "A source graded A or B that states the point, quoted verbatim with its locator and proposed as its own "
    "fact; the difference stays recorded as sources differ and is never settled by a writer."
)
DEAD_ACCEPTANCE = (
    "For each source, an archived snapshot of the same page (https://web.archive.org/web/<timestamp>/<url>) "
    "or the same work at its new canonical address, in which every quote is found again verbatim."
)
UNARCHIVED_ACCEPTANCE = (
    "For each source, a Wayback Machine snapshot (https://web.archive.org/web/<timestamp>/<url>) in which "
    "every quote is found verbatim."
)
PAGE_FORM_ACCEPTANCE = (
    "Every field that holds facts published as a section, every component registered by its label, and a "
    "layout record placing them by chapter, order and role; the page built from them matches the template."
)
PAGE_LAYOUT_ACCEPTANCE = (
    "A layout record naming each section and component by its label with its chapter, order and role, "
    "pictures with their crop; editing it never touches a fact."
)
PLAYBOOK = "the page playbook (kalavigyan://skills/references/playbook.md, guide page playbook/1)"
UPGRADE_ACCEPTANCE = (
    "The page rebuilt in a draft from the page as it stands, previewed with preview_page until neither its "
    "report nor your design critique holds anything you mean to fix, and proposed whole with propose_page; "
    "the task drops once the rebuilt page's layout is written."
)
UPGRADE_NOTHING = (
    "rule 29 finds nothing its facts state waiting for a figure, so read the page as it stands against the "
    "design critique (design-critique/1)"
)


@dataclass(frozen=True)
class Wording:
    needed: str
    acceptance: str
    items: Items = NO_ITEMS
    facts: bool = True


def counted(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def field_wording(kind: str, standing: SubjectStanding, discipline: str, held: FieldStanding) -> Wording:
    name, targets = standing.subject.name, standing.targets
    covers = DISCIPLINE_FIELDS[discipline]
    if kind == "SECTION":
        shown = (
            "no section is published"
            if held.section_sentences == 0
            else f"the published section has {counted(held.section_sentences, 'sentence')}"
        )
        return Wording(
            needed=f"{name} holds {counted(held.facts, 'fact')} under {discipline} ({covers}), but {shown}.",
            acceptance=(
                f"A section of at least {targets.section_sentences_min} sentences built from the stored facts, "
                "each sentence citing every fact it uses and adding nothing they do not say."
            ),
            items=Items(count=held.facts),
        )
    wanted = targets.facts_min - held.facts
    held_text = "no facts" if held.facts == 0 else counted(held.facts, "fact")
    return Wording(
        needed=f"{name} holds {held_text} under {discipline} ({covers}); the target is {targets.facts_min}.",
        acceptance=(
            f"At least {counted(wanted, 'more fact')} filed under {discipline}, each one sentence saying no more "
            f"than its quotes, each quote verbatim ({targets.quote_chars_min} to {targets.quote_chars_max} "
            "characters) with its locator from a source graded A to C, none repeating a stored fact."
        ),
        items=Items(count=wanted),
    )


def component_wording(standing: SubjectStanding, need: str, kinds: tuple[str, ...]) -> Wording:
    name = standing.subject.name
    return Wording(
        needed=(
            f"{name} has no {COMPONENT_NEED_TITLES[need]} in the component library "
            f"(kinds {', '.join(kinds)})."
        ),
        acceptance=(
            "list_components searched first: an existing component placed by its label when one fits, "
            f"otherwise a proposal that passes the library check, keyed to {name} or to the concept, "
            "compound or place it shows, and resting on stored facts."
        ),
    )


def page_form_wording(standing: SubjectStanding) -> Wording:
    return Wording(
        needed=(
            f"{standing.subject.name}'s page is not yet in the monograph form: its fields as sections, its "
            "components registered and a layout placing them."
        ),
        acceptance=PAGE_FORM_ACCEPTANCE,
    )


def page_layout_wording(standing: SubjectStanding) -> Wording:
    return Wording(
        needed=f"{standing.subject.name}'s page is in the monograph form but has no layout record.",
        acceptance=PAGE_LAYOUT_ACCEPTANCE,
    )


def upgrade_wording(standing: SubjectStanding, lines: tuple[str, ...]) -> Wording:
    shown = "; ".join(lines) if lines else UPGRADE_NOTHING
    return Wording(
        needed=(
            f"{standing.subject.name}'s page was built before the site drew what its facts now allow, and "
            f"nobody has rebuilt it. What its facts could now show: {shown}. Rebuild it by {PLAYBOOK}."
        ),
        acceptance=UPGRADE_ACCEPTANCE,
        items=Items(count=len(lines)),
    )


def second_source_wording(standing: SubjectStanding, discipline: str | None, items: Items) -> Wording:
    return Wording(
        needed=(
            f"{counted(items.count, 'fact')} of {standing.subject.name}{_under(discipline)} "
            f"{_rest(items.count)} on one source."
        ),
        acceptance=SECOND_SOURCE_ACCEPTANCE,
        items=items,
    )


def differ_wording(standing: SubjectStanding, discipline: str | None, items: Items) -> Wording:
    return Wording(
        needed=(
            f"{counted(items.count, 'fact')} of {standing.subject.name}{_under(discipline)} "
            f"{_be(items.count)} marked sources differ, waiting for a deciding source."
        ),
        acceptance=DIFFER_ACCEPTANCE,
        items=items,
    )


def dead_wording(standing: SubjectStanding) -> Wording:
    items = standing.dead_sources
    return Wording(
        needed=(
            f"{counted(items.count, 'source')} cited by {standing.subject.name} no longer "
            f"{'answers' if items.count == 1 else 'answer'} at {'its' if items.count == 1 else 'their'} address."
        ),
        acceptance=DEAD_ACCEPTANCE,
        items=items,
        facts=False,
    )


def unarchived_wording(standing: SubjectStanding) -> Wording:
    items = standing.unarchived_sources
    return Wording(
        needed=(
            f"{counted(items.count, 'source')} cited by {standing.subject.name} "
            f"{'has' if items.count == 1 else 'have'} no archived copy."
        ),
        acceptance=UNARCHIVED_ACCEPTANCE,
        items=items,
        facts=False,
    )


def review_needed(queue: str, waiting: QueueStanding) -> str:
    since = "" if waiting.oldest is None else f", the oldest since {waiting.oldest.date().isoformat()}"
    return f"{waiting.count} {REVIEW_QUEUE_LABELS[queue]} wait for review{since}."


def _under(discipline: str | None) -> str:
    return "" if discipline is None else f" under {discipline}"


def _rest(count: int) -> str:
    return "rests" if count == 1 else "rest"


def _be(count: int) -> str:
    return "is" if count == 1 else "are"
