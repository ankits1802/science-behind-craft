from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path
from typing import Any

import anthropic
import httpx

from atomic_write import write_text_atomically

from . import artifacts
from .connection import McpConnection, McpRefused
from .costs import CAP_CEILING_USD, CAP_DEFAULT_USD, Budget, Prices, dollars, prices_for, turn_cost
from .handed import HandedCall, client_tool, run_handed
from .loop import API_FAILED, OFF_LIST, LoopOutcome, run_loop
from .opinion import (
    DESIGN_SKILL,
    OPINION_RESERVE_USD,
    OpinionAsk,
    design_principles,
    opinion_params,
    opinion_text,
)
from .pictures import Picture
from .preview import design_notes, last_preview, preview_facts, preview_reply
from .progress import build_progress, progress_lines
from .request import (
    ALLOWED_TOOLS,
    HARNESS_ADDS,
    HARNESS_TOOLS,
    RunSettings,
    send_turn,
    system_prompt,
    user_turn,
)
from .spend import run_spend
from .summary import Evidence, summary_markdown
from .transcript import Call, RunFacts, all_calls

__all__ = ["command_line", "main"]

REPO_ROOT = Path(__file__).resolve().parents[2]
HTTP_TIMEOUT = httpx.Timeout(180.0, connect=20.0)
API_RETRIES = 4
FAILED_RUN = 1
FAILING_STOPS = (API_FAILED, OFF_LIST)
TOOL_FAILURES = (McpRefused, httpx.HTTPError)
HANDED = (
    "The run called preview_page itself for the model ({count} times) with read_pictures added, since the "
    "model cannot see pictures, so the server read each one's pictures; the run kept the pictures as files "
    "and the model got only the text, so no picture cost it a token."
)
SEEN = "Through the connector the model received {count} non-text items in tool results ({kinds})."
UNLISTED = "the server lists no {names}, which the run calls itself; nothing was sent to the model"

Ran = tuple[RunFacts, LoopOutcome, Budget, Prices]


@dataclass
class Progress:
    out: Path
    facts: RunFacts
    prices: Prices

    def __call__(self, outcome: LoopOutcome, budget: Budget) -> None:
        turn = outcome.turns[-1]
        names = [call.name for call in all_calls(outcome) if call.turn == turn.number]
        print(
            f"turn {turn.number}: {turn.message.get('stop_reason')}, {len(names)} tool calls"
            f" ({', '.join(names) or 'none'}), {dollars(turn.cost)}; spent {dollars(budget.spent)}",
            flush=True,
        )
        running = LoopOutcome("running", "", list(outcome.turns), list(outcome.handed))
        artifacts.write_transcript(self.out, self.facts, running)
        artifacts.write_cost(self.out, artifacts.Spend(self.facts, self.prices, outcome.turns, budget.spent))


def main(argv: Sequence[str] | None = None) -> int:
    args = command_line().parse_args(argv)
    if args.command == "revoke":
        return _revoke(args.token_file)
    return _run(args)


def _run(args: argparse.Namespace) -> int:
    facts = RunFacts(craft=args.craft, request=args.request, model=args.model, cap_usd=str(args.cap))
    prices = prices_for(args.model, datetime.now(UTC).date())
    opening = user_turn(args.request, args.craft)
    args.out.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(max_retries=API_RETRIES)
    with httpx.Client(timeout=HTTP_TIMEOUT) as http:
        server = McpConnection(args.token_file, http, mask=_mask)
        system = system_prompt(server.server, server.instructions())
        settings = RunSettings(args.model, server.server, system, _harness_tools(server.listed_tools()))
        budget = Budget(cap=args.cap - OPINION_RESERVE_USD)
        outcome = run_loop(
            partial(send_turn, client, settings, server.token),
            opening,
            budget=budget,
            prices=prices,
            allowed=ALLOWED_TOOLS,
            harness=partial(run_handed, server.call_tool, TOOL_FAILURES, HARNESS_ADDS),
            failures=(anthropic.APIError, *TOOL_FAILURES),
            report=Progress(args.out, facts, prices),
        )
    evidence = _evidence(client, (facts, outcome, budget, prices), args)
    write_text_atomically(args.out / artifacts.SUMMARY_FILE, summary_markdown(evidence))
    print(f"{outcome.stopped} ({outcome.detail}); spent {dollars(evidence.spent)} of ${facts.cap_usd}")
    print("\n".join(progress_lines(build_progress(evidence.calls, evidence.preview))), flush=True)
    return FAILED_RUN if outcome.stopped in FAILING_STOPS else 0


def _harness_tools(listed: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    found = {tool["name"]: tool for tool in listed if tool.get("name") in HARNESS_TOOLS}
    missing = sorted(HARNESS_TOOLS - set(found))
    if missing:
        raise McpRefused(UNLISTED.format(names=", ".join(missing)))
    return tuple(client_tool(found[name]) for name in sorted(found))


def _evidence(client: Any, run: Ran, args: argparse.Namespace) -> Evidence:
    facts, outcome, budget, prices = run
    artifacts.write_transcript(args.out, facts, outcome)
    calls = all_calls(outcome)
    found = last_preview(calls)
    drawn = _handed(outcome, found)
    reply = (drawn.structured or preview_reply(drawn.texts)) if drawn is not None else None
    notes = [*_seen_note(calls), HANDED.format(count=len(outcome.handed))]
    pictures = list(drawn.pictures) if drawn is not None else []
    read = design_notes(reply) if reply else ()
    asked = OpinionAsk(args.model, args.cap, read)
    opinion, opinion_usd = _second_opinion(client, asked, pictures, (budget, prices), notes)
    spend = run_spend(outcome, prices)
    kept = artifacts.Spend(facts, prices, outcome.turns, budget.spent, opinion_usd, spend.tools)
    artifacts.write_cost(args.out, kept)
    artifacts.write_json(args.out / artifacts.PREVIEW_FILE, {"reply": reply})
    artifacts.write_preview_urls(args.out, [("the model's last preview", (reply or {}).get("previewUrl"))])
    if opinion:
        write_text_atomically(args.out / artifacts.OPINION_FILE, opinion + "\n")
    return Evidence(
        facts=facts,
        outcome=outcome,
        calls=calls,
        spent=budget.spent + opinion_usd,
        spend=spend,
        preview=preview_facts(reply) if reply else None,
        pictures=artifacts.write_pictures(args.out, pictures),
        opinion=opinion,
        notes=notes,
        read=read,
    )


def _handed(outcome: LoopOutcome, found: Call | None) -> HandedCall | None:
    if found is None:
        return None
    return next((call for call in outcome.handed if call.call_id == found.call_id), None)


def _seen_note(calls: Sequence[Call]) -> list[str]:
    connector = [call for call in calls if not call.by_run]
    kinds = sorted({kind for call in connector for kind in call.other_content})
    count = sum(len(call.other_content) for call in connector)
    return [SEEN.format(count=count, kinds=", ".join(kinds))] if count else []


def _second_opinion(
    client: Any,
    asked: OpinionAsk,
    pictures: list[Picture],
    money: tuple[Budget, Prices],
    notes: list[str],
) -> tuple[str | None, Decimal]:
    budget, prices = money
    if not pictures:
        return None, Decimal(0)
    if asked.cap - budget.spent < OPINION_RESERVE_USD:
        notes.append(f"No second opinion: less than {dollars(OPINION_RESERVE_USD)} of the cap was left.")
        return None, Decimal(0)
    principles = design_principles((REPO_ROOT / DESIGN_SKILL).read_text(encoding="utf-8"))
    params = opinion_params(asked.model, principles, pictures, read=asked.read)
    try:
        with client.messages.stream(**params) as stream:
            message = stream.get_final_message().model_dump(mode="json")
    except anthropic.APIError as failed:
        notes.append(f"No second opinion: the API failed ({type(failed).__name__}).")
        return None, Decimal(0)
    return opinion_text(message) or None, turn_cost(message.get("usage") or {}, prices)


def _revoke(path: Path) -> int:
    if not path.is_file():
        print("No token file is left, so there is no connection to revoke.")
        return 0
    with httpx.Client(timeout=HTTP_TIMEOUT) as http:
        status = McpConnection(path, http, mask=_mask).revoke()
    path.unlink()
    print(f"Revoking the run's MCP connection answered HTTP {status}.")
    return 0 if status == httpx.codes.OK else FAILED_RUN


def _mask(value: str) -> None:
    print(f"::add-mask::{value}", flush=True)


def _cap(text: str) -> Decimal:
    try:
        cap = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"the cap is a number of US dollars, not {text!r}") from None
    if not cap.is_finite() or not OPINION_RESERVE_USD < cap <= CAP_CEILING_USD:
        raise argparse.ArgumentTypeError(
            f"the cap is more than {OPINION_RESERVE_USD} and at most {CAP_CEILING_USD} US dollars, not {text}"
        )
    return cap


def command_line() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A contributor's AI builds a page over MCP from one request."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="drive the model through the MCP connector and keep what it made")
    run.add_argument("--craft", required=True, help="the craft's slug, named in the request")
    run.add_argument("--request", required=True, help="what the contributor asks for")
    run.add_argument(
        "--cap",
        type=_cap,
        default=CAP_DEFAULT_USD,
        help=f"US dollars, at most {CAP_CEILING_USD}; {CAP_DEFAULT_USD} when absent",
    )
    run.add_argument("--model", required=True, help="the Claude model id")
    run.add_argument("--token-file", type=Path, required=True, help="the sign-in's token file")
    run.add_argument("--out", type=Path, required=True, help="the folder the run's artifacts are written to")
    revoke = commands.add_parser("revoke", help="revoke the run's MCP connection and delete its token file")
    revoke.add_argument("--token-file", type=Path, required=True, help="the sign-in's token file")
    return parser
