from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .preview import PREVIEW_TOOL, PreviewFacts
from .transcript import Call

__all__ = ["BRIEF_PART", "BuildProgress", "build_progress", "progress_lines"]

BRIEF_PART = "brief"
READ_TOOL, EDIT_TOOL = "get_page", "edit_draft"
NOT_REACHED = "not reached"


@dataclass(frozen=True)
class BuildProgress:
    briefs: int
    draft_turn: int | None
    edits: int
    facts: int
    components: int
    laid_out: bool
    previews: int
    last_failed: int | None


def build_progress(calls: Sequence[Call], preview: PreviewFacts | None) -> BuildProgress:
    done = [call for call in calls if call.answered and not call.is_error]
    edits = [call for call in done if call.name == EDIT_TOOL]
    added = [_added(call.arguments) for call in edits]
    return BuildProgress(
        briefs=sum(1 for call in done if call.name == READ_TOOL and BRIEF_PART in _parts(call.arguments)),
        draft_turn=edits[0].turn if edits else None,
        edits=len(edits),
        facts=sum(len(add.get("facts") or []) for add in added),
        components=sum(len(add.get("components") or []) for add in added),
        laid_out=any(add.get("layout") for add in added),
        previews=sum(1 for call in done if call.name == PREVIEW_TOOL),
        last_failed=preview.verdicts.get("failed") if preview is not None else None,
    )


def progress_lines(progress: BuildProgress) -> list[str]:
    draft = f"in turn {progress.draft_turn}" if progress.draft_turn is not None else NOT_REACHED
    added = (
        f"{progress.components} components and {progress.facts} facts in {progress.edits} edits"
        if progress.edits
        else NOT_REACHED
    )
    previewed = NOT_REACHED
    if progress.previews:
        failing = "" if progress.last_failed is None else f", the last failing {progress.last_failed} rules"
        previewed = f"{progress.previews} times{failing}"
    return [
        f"- Read the page's brief: {progress.briefs} calls.",
        f"- Opened a draft: {draft}.",
        f"- Added to the draft: {added}.",
        f"- Laid the page out: {'yes' if progress.laid_out else NOT_REACHED}.",
        f"- Previewed: {previewed}.",
    ]


def _parts(arguments: dict[str, Any]) -> list[Any]:
    parts = arguments.get("parts")
    return list(parts) if isinstance(parts, list) else []


def _added(arguments: dict[str, Any]) -> dict[str, Any]:
    add = arguments.get("add")
    return add if isinstance(add, dict) else {}
