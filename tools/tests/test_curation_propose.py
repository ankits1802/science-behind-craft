from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.curation.dossier import Dossier
from app.research.knowledge_writes import FactProposal, ProposalReply
from curation_support import REPO

from curation.proposing import FACTS_PATH, NotSendable, main, new_claims, proposal_of

AJRAKH = REPO / "backend" / "app" / "data" / "curation" / "Kutch-Ajrakh.json"
TOKEN = "session-token-of-a-researcher"
ENVIRON = {"KALAVIGYAN_TOKEN": TOKEN, "KALAVIGYAN_API": "https://api.example.org"}
NEW_TEXT = "A new fact the curator found, about the resist paste and how long it sits before washing."

Handler = Callable[[httpx.Request], httpx.Response]


def _plain() -> dict[str, Any]:
    return json.loads(AJRAKH.read_text(encoding="utf-8"))


def _multi_source(plain: dict[str, Any]) -> dict[str, Any]:
    return next(claim for claim in plain["claims"] if len({q["sourceId"] for q in claim["quotes"]}) >= 2)


def _reply(
    outcome: str, *, status: str = "DRAFT", gates: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    reply = ProposalReply(
        outcome=outcome,
        claim_id=uuid.uuid5(uuid.NAMESPACE_URL, outcome),
        status=status,
        level="PROVISIONAL",
        approved_at_once=False,
        in_review_queue=outcome != "REFUSED",
        sources_differ=False,
        differs_from=[],
        gates=gates or [],
        message=f"the fact is {outcome.lower()}",
    )
    return reply.model_dump(mode="json", by_alias=True)


def _files(tmp_path: Path, new_keys: list[str]) -> tuple[Path, Path]:
    plain = _plain()
    stored = {**plain, "claims": [claim for claim in plain["claims"] if claim["id"] not in new_keys]}
    working_file, stored_file = tmp_path / "work" / "Kutch-Ajrakh.json", tmp_path / "Kutch-Ajrakh.json"
    working_file.parent.mkdir()
    working_file.write_text(json.dumps(plain), encoding="utf-8")
    stored_file.write_text(json.dumps(stored), encoding="utf-8")
    return working_file, stored_file


def _run(
    argv: list[str], handler: Handler, environ: dict[str, str] = ENVIRON
) -> tuple[int, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return main(argv, environ=environ, transport=httpx.MockTransport(record)), seen


def test_a_new_fact_becomes_a_proposal_about_its_craft() -> None:
    plain = _plain()
    claim = _multi_source(plain)
    sources = {source["id"]: source for source in plain["sources"]}
    order = list(dict.fromkeys(quote["sourceId"] for quote in claim["quotes"]))
    proposal = proposal_of(Dossier.model_validate(plain), Dossier.model_validate(plain).claim(claim["id"]))
    sent = proposal.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert sent["subject"] == {"kind": "craft", "slug": "Kutch-Ajrakh"}
    assert (sent["field"], sent["statement"], sent["fields"]) == (claim["discipline"], claim["text"], [])
    assert [source["url"] for source in sent["sources"]] == [sources[key]["url"] for key in order]
    assert [source["title"] for source in sent["sources"]] == [sources[key]["title"] for key in order]
    assert [[(q["text"], q["locator"]) for q in source["quotes"]] for source in sent["sources"]] == [
        [(q["quote"], q["locator"]) for q in claim["quotes"] if q["sourceId"] == key] for key in order
    ]


def test_only_facts_the_stored_dossier_lacks_are_new() -> None:
    plain = _plain()
    first = plain["claims"][0]
    renumbered = {**first, "id": "C900", "text": first["text"].rstrip(".").upper() + "."}
    fresh = {**first, "id": "C901", "text": NEW_TEXT}
    working = Dossier.model_validate({**plain, "claims": [*plain["claims"], renumbered, fresh]})
    assert [claim.id for claim in new_claims(working, Dossier.model_validate(plain))] == ["C901"]
    assert len(new_claims(working, None)) == len(plain["claims"]) + 2


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"hypothesis": True}, "a hypothesis is not proposed"),
        ({"sensitivity": "RESTRICTED"}, "a RESTRICTED fact is not proposed"),
        ({"text": "Too short."}, "at least 20 characters"),
    ],
)
def test_a_fact_the_api_does_not_take_is_not_sent(change: dict[str, Any], reason: str) -> None:
    plain = _plain()
    plain["claims"][0] = {**plain["claims"][0], **change}
    dossier = Dossier.model_validate(plain)
    with pytest.raises(NotSendable, match=reason):
        proposal_of(dossier, dossier.claims[0])


def test_a_fact_resting_on_six_sources_is_not_sent() -> None:
    plain = _plain()
    quote = plain["claims"][0]["quotes"][0]
    keys = [source["id"] for source in plain["sources"][:6]]
    plain["claims"][0] = {**plain["claims"][0], "quotes": [{**quote, "sourceId": key} for key in keys]}
    dossier = Dossier.model_validate(plain)
    with pytest.raises(NotSendable, match="it cites 6 sources; a proposal takes at most 5"):
        proposal_of(dossier, dossier.claims[0])


def test_each_reply_is_reported_and_kept_in_the_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    keys = [claim["id"] for claim in _plain()["claims"][-3:]]
    working, stored = _files(tmp_path, keys)
    refused = [{"gate": "QUOTES", "passed": False, "reasons": ["the quote is not on the page"]}]
    replies = iter(
        [_reply("PUBLISHED", status="IN_REVIEW"), _reply("WAITING"), _reply("REFUSED", gates=refused)]
    )
    code, seen = _run(
        [str(working), "--stored", str(stored)], lambda _: httpx.Response(200, json=next(replies))
    )
    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert [str(request.url) for request in seen] == [f"https://api.example.org{FACTS_PATH}"] * 3
    assert {request.headers["authorization"] for request in seen} == {f"Bearer {TOKEN}"}
    statements = [FactProposal.model_validate_json(request.content).statement for request in seen]
    assert statements == [claim["text"] for claim in _plain()["claims"][-3:]]
    assert lines[0].startswith(f"{keys[0]}: PUBLISHED, claim ") and lines[0].endswith(
        "(IN_REVIEW, PROVISIONAL)"
    )
    assert lines[1].startswith(f"{keys[1]}: WAITING for review, claim ")
    assert lines[2] == f"{keys[2]}: REFUSED at QUOTES: the quote is not on the page"
    receipt = json.loads((working.parent / "Kutch-Ajrakh.proposals.json").read_text(encoding="utf-8"))
    assert {key: entry["outcome"] for key, entry in receipt["proposals"].items()} == dict(
        zip(keys, ["PUBLISHED", "WAITING", "REFUSED"], strict=True)
    )
    again, resent = _run([str(working), "--stored", str(stored)], lambda _: httpx.Response(500))
    assert (again, resent) == (0, [])
    assert capsys.readouterr().out.splitlines()[0] == (
        f"{keys[0]}: already proposed: PUBLISHED, claim {receipt['proposals'][keys[0]]['claimId']}"
    )


def test_a_fact_the_checks_could_not_run_on_is_sent_again_later(tmp_path: Path) -> None:
    key = _plain()["claims"][-1]["id"]
    working, stored = _files(tmp_path, [key])
    busy = httpx.Response(503, json={"detail": "The checks could not run just now; nothing was stored."})
    code, seen = _run([str(working), "--stored", str(stored)], lambda _: busy)
    assert (code, len(seen)) == (1, 1)
    assert not (working.parent / "Kutch-Ajrakh.proposals.json").exists()
    code, seen = _run(
        [str(working), "--stored", str(stored)], lambda _: httpx.Response(200, json=_reply("WAITING"))
    )
    assert (code, len(seen)) == (0, 1)


def test_a_refused_token_stops_the_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    keys = [claim["id"] for claim in _plain()["claims"][-2:]]
    working, stored = _files(tmp_path, keys)
    code, seen = _run(
        [str(working), "--stored", str(stored)],
        lambda _: httpx.Response(401, json={"detail": "This session is no longer valid. Sign in again."}),
    )
    lines = capsys.readouterr().out.splitlines()
    assert (code, len(seen)) == (2, 1)
    assert lines[0] == (
        f"{keys[0]}: the API refused the token (401): This session is no longer valid. Sign in again."
    )
    assert lines[1] == "stopped: no further fact was sent"


def test_a_dry_run_needs_no_token_and_sends_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claim = _multi_source(_plain())
    working, stored = _files(tmp_path, [claim["id"]])
    code, seen = _run([str(working), "--stored", str(stored), "--dry-run"], lambda _: httpx.Response(500), {})
    sources = len({quote["sourceId"] for quote in claim["quotes"]})
    assert (code, seen) == (0, [])
    assert capsys.readouterr().out.splitlines()[0] == (
        f"{claim['id']}: would send {sources} sources with {len(claim['quotes'])} quotes"
    )


def test_without_a_token_or_with_the_stored_file_itself_nothing_is_sent(tmp_path: Path) -> None:
    working, stored = _files(tmp_path, [_plain()["claims"][-1]["id"]])
    assert _run([str(working), "--stored", str(stored)], lambda _: httpx.Response(500), {}) == (2, [])
    assert _run([str(stored), "--stored", str(stored)], lambda _: httpx.Response(500)) == (2, [])
