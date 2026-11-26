from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from .costs import dollars
from .loop import LoopOutcome
from .preview import PreviewFacts
from .request import craft_name
from .transcript import Call, RunFacts

__all__ = ["PROBLEMS_SHOWN", "Evidence", "summary_markdown", "tool_counts"]

PROBLEMS_SHOWN = 12
NO_PREVIEW = "No preview_page call succeeded, so no page was drawn or checked."


@dataclass(frozen=True)
class Evidence:
    facts: RunFacts
    outcome: LoopOutcome
    calls: Sequence[Call]
    spent: Decimal
    preview: PreviewFacts | None = None
    pictures: Sequence[tuple[str, str]] = ()
    opinion: str | None = None
    notes: Sequence[str] = field(default_factory=tuple)


def tool_counts(calls: Sequence[Call]) -> list[tuple[str, int, int]]:
    made = Counter(call.name for call in calls)
    failed = Counter(call.name for call in calls if call.is_error)
    return sorted(
        ((name, count, failed[name]) for name, count in made.items()), key=lambda row: (-row[1], row[0])
    )


def summary_markdown(evidence: Evidence) -> str:
    sections = [
        _heading(evidence),
        _calls(evidence.calls),
        _components(evidence.preview),
        _verdicts(evidence.preview),
        _pictures(evidence.pictures),
        _opinion(evidence.opinion),
        _notes(evidence.notes),
    ]
    return "\n\n".join(section for section in sections if section) + "\n"


def _heading(evidence: Evidence) -> str:
    facts, outcome = evidence.facts, evidence.outcome
    return "\n".join(
        [
            f"## Agent acceptance: {craft_name(facts.craft)}",
            "",
            f"The request: “{facts.request}” Model `{facts.model}`, cap ${facts.cap_usd}.",
            f"Stopped: {outcome.stopped} ({outcome.detail}) after {len(outcome.turns)} turns.",
            f"Cost: {dollars(evidence.spent)} of ${facts.cap_usd}.",
        ]
    )


def _calls(calls: Sequence[Call]) -> str:
    rows = [f"| `{name}` | {count} | {failed} |" for name, count, failed in tool_counts(calls)]
    if not rows:
        return "### Tool calls\n\nThe model called no tool."
    head = f"### Tool calls ({len(calls)})\n\n| Tool | Calls | Errors |\n|---|---|---|"
    return "\n".join([head, *rows])


def _components(preview: PreviewFacts | None) -> str:
    if preview is None:
        return f"### Components delivered, by kind\n\n{NO_PREVIEW}"
    rows = [f"| `{kind}` | {count} |" for kind, count in sorted(preview.figure_kinds.items())]
    total = f"The last preview draws {preview.components} components."
    if not rows:
        return f"### Components delivered, by kind\n\n{total} It names no figure kind."
    return "\n".join([f"### Components delivered, by kind\n\n{total}\n\n| Kind | Count |\n|---|---|", *rows])


def _verdicts(preview: PreviewFacts | None) -> str:
    if preview is None:
        return ""
    counts = preview.verdicts
    lines = [
        "### The last preview's verdicts",
        "",
        f"{counts.get('passed', 0)} rules pass, {counts.get('failed', 0)} fail, "
        f"{counts.get('judged', 0)} are left to judge on the private link.",
    ]
    lines += [f"- Fails rule {rule}" for rule in preview.failed_rules]
    lines.append(
        f"\nDrawing: {preview.drawing_state or 'not drawn'}, {len(preview.drawing_problems)} problems."
    )
    lines += [f"- {problem}" for problem in preview.drawing_problems[:PROBLEMS_SHOWN]]
    if len(preview.drawing_problems) > PROBLEMS_SHOWN:
        lines.append(f"- and {len(preview.drawing_problems) - PROBLEMS_SHOWN} more, in preview.json")
    if preview.beside_bar:
        lines.append(f"\nBeside Kutch Ajrakh: {', '.join(preview.beside_bar)}.")
    lines.append(f"\nPrivate link: {preview.preview_url or 'none'}")
    return "\n".join(lines)


def _pictures(pictures: Sequence[tuple[str, str]]) -> str:
    if not pictures:
        return "### Pictures\n\nNo picture was kept."
    return "\n".join(["### Pictures", "", *(f"- `{name}`: {caption}" for name, caption in pictures)])


def _opinion(opinion: str | None) -> str:
    if not opinion:
        return ""
    return f"### A second opinion on the pictures (never the verdict)\n\n{opinion}"


def _notes(notes: Sequence[str]) -> str:
    return "\n".join(["### Notes", "", *(f"- {note}" for note in notes)]) if notes else ""
