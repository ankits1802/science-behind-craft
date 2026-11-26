from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from .costs import dollars
from .loop import LoopOutcome
from .preview import PreviewFacts
from .progress import build_progress, progress_lines
from .request import craft_name
from .spend import CHARS_PER_TOKEN, RunSpend
from .transcript import Call, RunFacts, trimmed

__all__ = ["ERROR_CHARS", "PROBLEMS_SHOWN", "Evidence", "summary_markdown"]

PROBLEMS_SHOWN = 12
ERROR_CHARS = 600
KILO = 1000
NO_PREVIEW = "No preview_page call succeeded, so no page was drawn or checked."
SPEND_NOTE = (
    "Est. $ is an estimate the API does not report per tool: each argument and result at {chars} characters a "
    "token, paid once as output when the model wrote it, written to the cache once and read by every later "
    "request ({requests} in this run). The turns cost {input} of input and {output} of output; the rest of the "
    "input is the prompt, the tool list and the model's own thinking and text."
)


@dataclass(frozen=True)
class Evidence:
    facts: RunFacts
    outcome: LoopOutcome
    calls: Sequence[Call]
    spent: Decimal
    spend: RunSpend | None = None
    preview: PreviewFacts | None = None
    pictures: Sequence[tuple[str, str]] = ()
    opinion: str | None = None
    notes: Sequence[str] = field(default_factory=tuple)


def summary_markdown(evidence: Evidence) -> str:
    sections = [
        _heading(evidence),
        _progress(evidence),
        _calls(evidence.calls, evidence.spend),
        _errors(evidence.calls),
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


def _progress(evidence: Evidence) -> str:
    lines = progress_lines(build_progress(evidence.calls, evidence.preview))
    return "\n".join(["### How far the build got", "", *lines])


def _calls(calls: Sequence[Call], spend: RunSpend | None) -> str:
    if not calls:
        return "### Tool calls\n\nThe model called no tool."
    head = f"### Tool calls ({len(calls)})\n\n| Tool | Calls | Errors | Result KB | Est. tokens | Est. $ |"
    rows = [
        f"| `{row.name}` | {row.calls} | {row.errors} | {row.result_chars / KILO:.1f} | {row.tokens:,} | "
        f"{dollars(row.usd)} |"
        for row in (spend.tools if spend is not None else [])
    ]
    note = (
        SPEND_NOTE.format(
            chars=CHARS_PER_TOKEN,
            requests=spend.requests,
            input=dollars(spend.input_usd),
            output=dollars(spend.output_usd),
        )
        if spend is not None
        else ""
    )
    return "\n".join([head, "|---|---|---|---|---|---|", *rows, "", note]).rstrip()


def _errors(calls: Sequence[Call]) -> str:
    failed = [call for call in calls if call.is_error]
    if not failed:
        return ""
    lines = [
        f"- Turn {call.turn}, `{call.name}`: {trimmed(' '.join(' '.join(call.texts).split()), ERROR_CHARS)}"
        for call in failed
    ]
    return "\n".join([f"### Tool errors ({len(failed)})", "", *lines])


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
