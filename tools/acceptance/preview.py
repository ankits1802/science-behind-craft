from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.research.page_report_rules import FAIL

from .transcript import Call

__all__ = [
    "BAR_COUNTS",
    "PREVIEW_TOOL",
    "PreviewFacts",
    "last_preview",
    "preview_facts",
    "preview_reply",
]

PREVIEW_TOOL = "preview_page"
BAR_COUNTS = ("pictures", "figures", "interactives", "maps")


@dataclass(frozen=True)
class PreviewFacts:
    preview_url: str | None
    components: int | None
    figure_kinds: dict[str, int]
    verdicts: dict[str, int]
    failed_rules: tuple[str, ...]
    drawing_state: str | None
    drawing_problems: tuple[str, ...]
    picture_names: tuple[str, ...]
    beside_bar: tuple[str, ...]


def last_preview(calls: Sequence[Call]) -> Call | None:
    drawn = [call for call in calls if call.name == PREVIEW_TOOL and call.answered and not call.is_error]
    return drawn[-1] if drawn else None


def preview_reply(texts: Sequence[str]) -> dict[str, Any] | None:
    if not texts:
        return None
    try:
        reply = json.loads(texts[0])
    except json.JSONDecodeError:
        return None
    return reply if isinstance(reply, dict) else None


def preview_facts(reply: dict[str, Any]) -> PreviewFacts:
    report = reply.get("report") or {}
    drawing = report.get("drawing") or {}
    return PreviewFacts(
        preview_url=reply.get("previewUrl"),
        components=reply.get("components"),
        figure_kinds=dict(report.get("figureKinds") or {}),
        verdicts={name: report[name] for name in ("passed", "failed", "judged") if name in report},
        failed_rules=tuple(
            f"{rule.get('rule')}. {rule.get('title')}"
            for rule in report.get("rules") or []
            if rule.get("verdict") == FAIL
        ),
        drawing_state=drawing.get("state"),
        drawing_problems=tuple(
            f"{problem.get('width')} px, {problem.get('label')}: {problem.get('problem')}"
            for problem in drawing.get("problems") or []
        ),
        picture_names=tuple(str(image.get("name")) for image in drawing.get("images") or []),
        beside_bar=_beside_bar(report.get("bar") or {}),
    )


def _beside_bar(bar: dict[str, Any]) -> tuple[str, ...]:
    page, ajrakh = bar.get("page") or {}, bar.get("bar") or {}
    if not page or not ajrakh:
        return ()
    return tuple(f"{name} {page.get(name, 0)} of {ajrakh.get(name, 0)}" for name in BAR_COUNTS)
