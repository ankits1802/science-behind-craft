from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .published_edits import FieldChange, field_changes
from .review_queue import APPROVE, RAISE, REJECT, RETRACT
from .staged_reviews import CLEAR, CORRECT, EDIT, REMOVE, SourceFix, StagedDecision

__all__ = ["PROPOSAL_REVIEW_PATH", "PageTouches", "decision_words", "proposal_review_link"]

PROPOSAL_REVIEW_PATH = "/admin/review?proposal={id}"
VERBS = MappingProxyType(
    {
        APPROVE: "Approve",
        REJECT: "Reject",
        RAISE: "Approve as reviewed",
        RETRACT: "Retract",
        CORRECT: "Correct",
        CLEAR: "Clear",
    }
)
EFFECTS = MappingProxyType(
    {
        APPROVE: "it is published for readers",
        REJECT: "it is not published, and whoever gave it reads the reason",
        RAISE: "it is published as reviewed, its evidence level raised",
        RETRACT: "it is taken off every page that shows it",
        CORRECT: "the source's record changes: {fields}",
        CLEAR: "the mark that its sources differ is taken off",
        REMOVE: "readers no longer see it there, and the record keeps it",
        EDIT: "readers see it changed ({fields}), and the record keeps the old version",
    }
)
PAGE_PAST = MappingProxyType({APPROVE: "approved", REJECT: "rejected"})
QUEUE_LINE = "{verb} “{label}”: {effect}."
PUBLISHED_LINE = "{label}: {effect}."
PAGE_LINE = "{verb} “{label}”: each part of it that still waits is {past} through its own queue's checks."
FILED_UNDER_CRAFT = " It is filed under the craft {slug}."
FILED_UNDER_FAMILY = " It is filed under the science of the family {slug}."
TOUCHES = " It touches {what}."
CHAPTERS = "the chapter {names}"
CHAPTERS_MANY = "the chapters {names}"
COMPONENTS = "the component {names}"
COMPONENTS_MANY = "the components {names}"
LINK = " The page as it stood and as it will be, for reviewers only: {link}"
REASON = " The reason given: “{reason}”"
SOURCE_FIELDS = MappingProxyType(
    {"title": "title", "authors": "authors", "year": "year", "container_title": "journal", "kind": "kind"}
)


@dataclass(frozen=True)
class PageTouches:
    chapters: tuple[str, ...]
    components: tuple[str, ...]
    link: str


def proposal_review_link(site: str, proposal_id: uuid.UUID) -> str:
    return f"{site}{PROPOSAL_REVIEW_PATH.format(id=proposal_id)}"


def decision_words(decision: StagedDecision, label: str, *, touches: PageTouches | None = None) -> str:
    if decision.page is not None:
        said = PAGE_LINE.format(
            verb=VERBS[decision.action], label=label, past=PAGE_PAST.get(decision.action, decision.action)
        )
        said += "" if touches is None else _touched(touches)
    elif decision.action in (REMOVE, EDIT):
        said = PUBLISHED_LINE.format(label=label, effect=_effect(decision))
    else:
        said = QUEUE_LINE.format(verb=VERBS[decision.action], label=label, effect=_effect(decision))
        said += _filing(decision)
    return said + REASON.format(reason=decision.reason)


def _effect(decision: StagedDecision) -> str:
    effect = EFFECTS[decision.action]
    if decision.action == EDIT and decision.edit is not None:
        return effect.format(fields="; ".join(_change(change) for change in field_changes(decision.edit)))
    if decision.action == CORRECT and decision.source is not None:
        return effect.format(fields=_source_fields(decision.source))
    return effect


def _change(change: FieldChange) -> str:
    if change.after is None:
        return f"{change.field} is cleared"
    if change.before is None:
        return f"{change.field} becomes “{change.after}”"
    return f"{change.field} “{change.before}” becomes “{change.after}”"


def _source_fields(fix: SourceFix) -> str:
    given = fix.model_dump(exclude_none=True, by_alias=False)
    return ", ".join(f"{SOURCE_FIELDS[name]} {_shown(value)}" for name, value in given.items())


def _shown(value: object) -> str:
    if isinstance(value, list):
        return _listed([str(item) for item in value])
    return f"“{value}”" if isinstance(value, str) else str(value)


def _filing(decision: StagedDecision) -> str:
    if decision.craft is not None:
        return FILED_UNDER_CRAFT.format(slug=decision.craft)
    if decision.family is not None:
        return FILED_UNDER_FAMILY.format(slug=decision.family)
    return ""


def _touched(touches: PageTouches) -> str:
    parts = []
    if touches.chapters:
        named = CHAPTERS if len(touches.chapters) == 1 else CHAPTERS_MANY
        parts.append(named.format(names=_listed(touches.chapters)))
    if touches.components:
        named = COMPONENTS if len(touches.components) == 1 else COMPONENTS_MANY
        parts.append(named.format(names=_listed(touches.components)))
    said = TOUCHES.format(what=", and ".join(parts)) if parts else ""
    return said + LINK.format(link=touches.link)


def _listed(names: Sequence[str]) -> str:
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"
