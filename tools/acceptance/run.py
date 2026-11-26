from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
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
from .costs import CAP_CEILING_USD, Budget, Prices, dollars, prices_for, turn_cost
from .loop import API_FAILED, OFF_LIST, LoopOutcome, Turn, run_loop
from .opinion import DESIGN_SKILL, OPINION_RESERVE_USD, design_principles, opinion_params, opinion_text
from .preview import PREVIEW_TOOL, Picture, last_preview, preview_facts, preview_reply, reply_pictures
from .request import ALLOWED_TOOLS, RunSettings, send_turn, system_prompt, user_turn
from .summary import Evidence, summary_markdown
from .transcript import Call, RunFacts, paired_calls, trimmed

__all__ = ["main"]

REPO_ROOT = Path(__file__).resolve().parents[2]
HTTP_TIMEOUT = httpx.Timeout(180.0, connect=20.0)
API_RETRIES = 4
FAILED_RUN = 1
FAILING_STOPS = (API_FAILED, OFF_LIST)
REDRAWN = (
    "The connector hands the model the text of each tool result only, so the pictures were drawn again "
    "after the run from the last preview_page call's arguments: one more private preview of the same draft."
)
SEEN = "Through the connector the model received {count} non-text items in tool results ({kinds})."
UNSEEN = "Through the connector the model received no picture: every tool result reached it as text only."

Ran = tuple[RunFacts, LoopOutcome, Budget, Prices]


@dataclass
class Progress:
    out: Path
    facts: RunFacts
    prices: Prices
    turns: list[Turn] = field(default_factory=list)

    def __call__(self, turn: Turn, budget: Budget) -> None:
        self.turns.append(turn)
        names = [
            block.get("name")
            for block in turn.message.get("content") or []
            if block.get("type") == "mcp_tool_use"
        ]
        print(
            f"turn {turn.number}: {turn.message.get('stop_reason')}, {len(names)} tool calls"
            f" ({', '.join(names) or 'none'}), {dollars(turn.cost)}; spent {dollars(budget.spent)}",
            flush=True,
        )
        artifacts.write_transcript(self.out, self.facts, LoopOutcome("running", "", list(self.turns)))
        artifacts.write_cost(self.out, artifacts.Spend(self.facts, self.prices, self.turns, budget.spent))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
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
        settings = RunSettings(args.model, server.server, system_prompt(server.server, server.instructions()))
        budget = Budget(cap=args.cap - OPINION_RESERVE_USD)
        outcome = run_loop(
            partial(send_turn, client, settings, server.token),
            opening,
            budget=budget,
            prices=prices,
            allowed=ALLOWED_TOOLS,
            failures=(anthropic.APIError, McpRefused, httpx.HTTPError),
            report=Progress(args.out, facts, prices),
        )
        evidence = _evidence(client, server, (facts, outcome, budget, prices), args)
    write_text_atomically(args.out / artifacts.SUMMARY_FILE, summary_markdown(evidence))
    print(
        f"{outcome.stopped} ({outcome.detail}); spent {dollars(evidence.spent)} of ${facts.cap_usd}",
        flush=True,
    )
    return FAILED_RUN if outcome.stopped in FAILING_STOPS else 0


def _evidence(client: Any, server: McpConnection, run: Ran, args: argparse.Namespace) -> Evidence:
    facts, outcome, budget, prices = run
    artifacts.write_transcript(args.out, facts, outcome)
    artifacts.write_cost(args.out, artifacts.Spend(facts, prices, outcome.turns, budget.spent))
    calls = paired_calls(outcome.turns)
    notes = [_seen_note(calls)]
    found = last_preview(calls)
    reply = preview_reply(found.texts) if found is not None else None
    pictures, drawn = _redrawn(server, found, notes) if found is not None else ([], None)
    opinion, opinion_usd = _second_opinion(client, (args.model, args.cap), pictures, (budget, prices), notes)
    artifacts.write_cost(args.out, artifacts.Spend(facts, prices, outcome.turns, budget.spent, opinion_usd))
    artifacts.write_json(args.out / artifacts.PREVIEW_FILE, {"asTheModelGotIt": reply, "drawnAgain": drawn})
    drawn_url = drawn.get("previewUrl") if drawn else None
    model_url = reply.get("previewUrl") if reply else None
    artifacts.write_preview_urls(
        args.out, [("the model's last preview", model_url), ("drawn again", drawn_url)]
    )
    if opinion:
        write_text_atomically(args.out / artifacts.OPINION_FILE, opinion + "\n")
    return Evidence(
        facts=facts,
        outcome=outcome,
        calls=calls,
        spent=budget.spent + opinion_usd,
        preview=preview_facts(reply) if reply else None,
        pictures=artifacts.write_pictures(args.out, pictures),
        opinion=opinion,
        notes=notes,
    )


def _seen_note(calls: Sequence[Call]) -> str:
    kinds = sorted({kind for call in calls for kind in call.other_content})
    count = sum(len(call.other_content) for call in calls)
    return SEEN.format(count=count, kinds=", ".join(kinds)) if count else UNSEEN


def _redrawn(
    server: McpConnection, found: Call, notes: list[str]
) -> tuple[list[Picture], dict[str, Any] | None]:
    try:
        result = server.call_tool(PREVIEW_TOOL, found.arguments)
    except (McpRefused, httpx.HTTPError) as failed:
        notes.append(f"The last preview could not be drawn again for its pictures: {failed}")
        return [], None
    if result.get("isError"):
        said = " ".join(item.get("text", "") for item in result.get("content") or [])
        notes.append(f"Drawing the last preview again answered an error: {trimmed(said, 400)}")
        return [], None
    notes.append(REDRAWN)
    return reply_pictures(result.get("content") or []), result.get("structuredContent")


def _second_opinion(
    client: Any,
    asked: tuple[str, Decimal],
    pictures: list[Picture],
    money: tuple[Budget, Prices],
    notes: list[str],
) -> tuple[str | None, Decimal]:
    (model, cap), (budget, prices) = asked, money
    if not pictures:
        return None, Decimal(0)
    if cap - budget.spent < OPINION_RESERVE_USD:
        notes.append(f"No second opinion: less than {dollars(OPINION_RESERVE_USD)} of the cap was left.")
        return None, Decimal(0)
    principles = design_principles((REPO_ROOT / DESIGN_SKILL).read_text(encoding="utf-8"))
    try:
        with client.messages.stream(**opinion_params(model, principles, pictures)) as stream:
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A contributor's AI builds a page over MCP from one request."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="drive the model through the MCP connector and keep what it made")
    run.add_argument("--craft", required=True, help="the craft's slug, named in the request")
    run.add_argument("--request", required=True, help="what the contributor asks for")
    run.add_argument("--cap", type=_cap, required=True, help=f"US dollars, at most {CAP_CEILING_USD}")
    run.add_argument("--model", required=True, help="the Claude model id")
    run.add_argument("--token-file", type=Path, required=True, help="the sign-in's token file")
    run.add_argument("--out", type=Path, required=True, help="the folder the run's artifacts are written to")
    revoke = commands.add_parser("revoke", help="revoke the run's MCP connection and delete its token file")
    revoke.add_argument("--token-file", type=Path, required=True, help="the sign-in's token file")
    return parser
