from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

import httpx
from app.curation.dossier import CATEGORY_SCOPE, Dossier, parse_dossier
from app.curation.files import CATEGORIES_DIR_NAME, CURATION_DIR
from app.curation.parts import CitedQuote, Claim
from app.research.knowledge_writes import (
    PROPOSAL_QUOTES_MAX,
    PROPOSAL_SOURCES_MAX,
    FactProposal,
    ProposalReply,
)
from app.research.review_switch import REFUSED, WAITING
from pydantic import ValidationError

from .output import relative_label, utf8_console, write_text_atomically

__all__ = [
    "FACTS_PATH",
    "Answer",
    "NotSendable",
    "ProposalRun",
    "Receipt",
    "Stop",
    "api_client",
    "folded",
    "main",
    "new_claims",
    "proposal_digest",
    "proposal_of",
    "receipt_path",
    "reply_line",
    "send",
    "stored_path",
]

FACTS_PATH = "/api/knowledge/facts"
TOKEN_ENV = "KALAVIGYAN_TOKEN"
API_ENV = "KALAVIGYAN_API"
USER_AGENT = "kalavigyan-curation-propose/1"
RECEIPT_SUFFIX = ".proposals.json"
TIMEOUT_SECONDS = 300
USAGE = 2
OPEN = "OPEN"
RECEIPT_SCHEMA_VERSION = 1
STOPPING_STATUSES = (401, 403)
NOT_STORED_STATUSES = (422, 503)


class NotSendable(ValueError):
    pass


class Stop(RuntimeError):
    pass


@dataclass(frozen=True)
class Answer:
    line: str
    reply: ProposalReply | None = None


@dataclass
class Receipt:
    slug: str
    proposals: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path, slug: str) -> Receipt:
        if not path.is_file():
            return cls(slug=slug)
        plain = json.loads(path.read_text(encoding="utf-8"))
        return cls(slug=slug, proposals=dict(plain.get("proposals") or {}))

    def text(self) -> str:
        plain = {"schemaVersion": RECEIPT_SCHEMA_VERSION, "slug": self.slug, "proposals": self.proposals}
        return json.dumps(plain, ensure_ascii=False, indent=2) + "\n"

    def answered(self, key: str, digest: str) -> dict[str, Any] | None:
        found = self.proposals.get(key)
        return found if found and found.get("digest") == digest else None

    def record(self, key: str, digest: str, reply: ProposalReply) -> None:
        self.proposals[key] = {
            "digest": digest,
            "outcome": reply.outcome,
            "claimId": str(reply.claim_id),
            "status": reply.status,
            "message": reply.message,
        }


def folded(text: str) -> str:
    return text.strip().rstrip(" .").lower()


def new_claims(working: Dossier, stored: Dossier | None) -> list[Claim]:
    if stored is None:
        return list(working.claims)
    keys = {claim.id for claim in stored.claims}
    texts = {folded(claim.text) for claim in stored.claims}
    return [claim for claim in working.claims if claim.id not in keys and folded(claim.text) not in texts]


def proposal_of(dossier: Dossier, claim: Claim) -> FactProposal:
    if claim.hypothesis:
        raise NotSendable("a hypothesis is not proposed; the API takes quoted facts")
    if claim.sensitivity != OPEN:
        raise NotSendable(f"a {claim.sensitivity} fact is not proposed through the open API")
    quoted: dict[str, list[CitedQuote]] = defaultdict(list)
    for quote in claim.quotes:
        quoted[quote.source_id].append(quote)
    if len(quoted) > PROPOSAL_SOURCES_MAX:
        raise NotSendable(f"it cites {len(quoted)} sources; a proposal takes at most {PROPOSAL_SOURCES_MAX}")
    crowded = [key for key, quotes in quoted.items() if len(quotes) > PROPOSAL_QUOTES_MAX]
    if crowded:
        raise NotSendable(f"{', '.join(crowded)} gives more than {PROPOSAL_QUOTES_MAX} quotes")
    try:
        return FactProposal.model_validate(_plain_proposal(dossier, claim, quoted))
    except ValidationError as error:
        raise NotSendable("; ".join(problem["msg"] for problem in error.errors())) from error


def _plain_proposal(dossier: Dossier, claim: Claim, quoted: dict[str, list[CitedQuote]]) -> dict[str, Any]:
    kind = "category" if dossier.scope == CATEGORY_SCOPE else "craft"
    sources = []
    for source_id, quotes in quoted.items():
        source = dossier.source(source_id)
        sources.append(
            {
                "url": source.url,
                "title": source.title,
                "licence": source.licence,
                "quotes": [{"text": quote.quote, "locator": quote.locator} for quote in quotes],
            }
        )
    return {
        "subject": {"kind": kind, "slug": dossier.slug},
        "field": claim.discipline,
        "statement": claim.text,
        "sources": sources,
    }


def proposal_digest(proposal: FactProposal) -> str:
    return hashlib.sha256(proposal.model_dump_json(by_alias=True).encode("utf-8")).hexdigest()


def send(client: httpx.Client, proposal: FactProposal) -> Answer:
    body = proposal.model_dump(mode="json", by_alias=True, exclude_none=True)
    try:
        response = client.post(FACTS_PATH, json=body)
    except httpx.HTTPError as error:
        raise Stop(f"the API could not be reached: {error}") from error
    detail = _detail(response)
    if response.status_code in STOPPING_STATUSES:
        raise Stop(f"the API refused the token ({response.status_code}): {detail}")
    if response.status_code in NOT_STORED_STATUSES:
        return Answer(f"not stored ({response.status_code}): {detail}")
    if response.status_code != httpx.codes.OK:
        return Answer(f"failed ({response.status_code}): {detail}")
    reply = ProposalReply.model_validate(response.json())
    return Answer(reply_line(reply), reply)


def reply_line(reply: ProposalReply) -> str:
    if reply.outcome == REFUSED:
        failed = next((gate for gate in reply.gates if not gate.passed), None)
        reasons = "; ".join(failed.reasons) if failed else reply.message
        return f"REFUSED at {failed.gate if failed else 'a gate'}: {reasons}"
    shown = f"claim {reply.claim_id} ({reply.status}, {reply.level})"
    if reply.outcome == WAITING:
        return f"WAITING for review, {shown}"
    return f"PUBLISHED, {shown}" + (", approved at once" if reply.approved_at_once else "")


def _detail(response: httpx.Response) -> str:
    try:
        plain = response.json()
    except ValueError:
        return response.text[:200] or response.reason_phrase
    found = plain.get("detail") if isinstance(plain, dict) else None
    return str(found) if found else response.reason_phrase


Sender = Callable[[FactProposal], Answer]


@dataclass
class ProposalRun:
    receipt: Receipt
    sender: Sender | None
    lines: list[str] = field(default_factory=list)
    failed: int = 0
    stopped: bool = False

    def propose(self, dossier: Dossier, claims: Sequence[Claim]) -> ProposalRun:
        for claim in claims:
            if self.stopped:
                break
            self.lines.append(f"{claim.id}: {self._one(dossier, claim)}")
        if self.stopped:
            self.lines.append("stopped: no further fact was sent")
        return self

    def _one(self, dossier: Dossier, claim: Claim) -> str:
        try:
            proposal = proposal_of(dossier, claim)
        except NotSendable as reason:
            self.failed += 1
            return f"not sent: {reason}"
        digest = proposal_digest(proposal)
        earlier = self.receipt.answered(claim.id, digest)
        if earlier is not None:
            return f"already proposed: {earlier['outcome']}, claim {earlier['claimId']}"
        if self.sender is None:
            quotes = sum(len(source.quotes) for source in proposal.sources)
            return f"would send {len(proposal.sources)} sources with {quotes} quotes"
        try:
            answer = self.sender(proposal)
        except Stop as stop:
            self.failed += 1
            self.stopped = True
            return str(stop)
        if answer.reply is None:
            self.failed += 1
        else:
            self.receipt.record(claim.id, digest, answer.reply)
        return answer.line


def stored_path(dossier: Dossier) -> Path:
    folder = CURATION_DIR / CATEGORIES_DIR_NAME if dossier.scope == CATEGORY_SCOPE else CURATION_DIR
    return folder / f"{dossier.slug}.json"


def receipt_path(working: Path, dossier: Dossier) -> Path:
    return working.with_name(f"{dossier.slug}{RECEIPT_SUFFIX}")


def api_client(api: str, token: str | None, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=api, headers=headers, timeout=TIMEOUT_SECONDS, transport=transport)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="propose",
        description=(
            "Send a working dossier's new facts through POST /api/knowledge/facts, where they pass the gates. "
            f"The token is read from {TOKEN_ENV}: a signed-in session token of a Researcher or above."
        ),
    )
    parser.add_argument("dossier", type=Path, help="the working dossier holding the new facts")
    parser.add_argument(
        "--stored", type=Path, help="the dossier the database exported (default: the one in git)"
    )
    parser.add_argument("--api", help=f"the API origin, PUBLIC_API_URL, not the site (default: {API_ENV})")
    parser.add_argument(
        "--receipt", type=Path, help="where the replies are kept (default: beside the dossier)"
    )
    parser.add_argument("--only", action="append", default=[], help="a claim id to send; repeat it")
    parser.add_argument("--dry-run", action="store_true", help="show what would be sent and send nothing")
    return parser


def _dossier(path: Path) -> Dossier:
    try:
        return parse_dossier(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as error:
        raise Stop(f"{relative_label(path)} is not a readable dossier: {error}") from error


def _inputs(args: argparse.Namespace, environ: Mapping[str, str]) -> tuple[Dossier, Dossier | None, str]:
    working = _dossier(args.dossier)
    stored_file = args.stored or stored_path(working)
    if stored_file.resolve() == args.dossier.resolve():
        raise Stop("the working dossier is the stored one; work on a copy of the export")
    api = args.api or environ.get(API_ENV) or ""
    if not args.dry_run and not (api and environ.get(TOKEN_ENV)):
        raise Stop(f"set {API_ENV} to the API origin and {TOKEN_ENV} to a signed-in session token")
    return working, _dossier(stored_file) if stored_file.is_file() else None, api


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    transport: httpx.BaseTransport | None = None,
) -> int:
    utf8_console()
    args = _parser().parse_args(argv)
    try:
        working, stored, api = _inputs(args, environ)
    except Stop as stop:
        print(stop)
        return USAGE
    claims = [claim for claim in new_claims(working, stored) if not args.only or claim.id in args.only]
    receipt_file = args.receipt or receipt_path(args.dossier, working)
    run = ProposalRun(receipt=Receipt.read(receipt_file, working.slug), sender=None)
    with api_client(api, environ.get(TOKEN_ENV), transport) as client:
        if not args.dry_run:
            run.sender = partial(send, client)
        try:
            run.propose(working, claims)
        finally:
            if run.receipt.proposals:
                write_text_atomically(receipt_file, run.receipt.text())
    summary = f"{len(claims)} new facts in {relative_label(args.dossier)}, {run.failed} failed"
    print("\n".join([*run.lines, summary]))
    return USAGE if run.stopped else int(run.failed > 0)
