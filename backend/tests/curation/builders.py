from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from app.curation.check_file import VERIFY_TOOL, CheckFile, QuoteCheckEntry, SourceCheck, verified_digest
from app.curation.dossier import Dossier

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PASSING = FIXTURES / "passing" / "Kutch-Ajrakh.json"
FAILING = FIXTURES / "failing" / "Kutch-Ajrakh.json"
CHECKED_AT = datetime.fromisoformat("2026-11-17T12:00:00+05:30")
TEXT_SHA256 = "0" * 64


def passing_plain() -> dict[str, Any]:
    return json.loads(PASSING.read_text(encoding="utf-8"))


def passing_dossier() -> Dossier:
    return Dossier.model_validate(passing_plain())


def failing_dossier() -> Dossier:
    return Dossier.model_validate_json(FAILING.read_text(encoding="utf-8"))


def changed_dossier(change: Callable[[dict[str, Any]], None]) -> Dossier:
    plain = passing_plain()
    change(plain)
    return Dossier.model_validate(plain)


def check_for(
    dossier: Dossier, *, failing: frozenset[str] = frozenset(), unread: frozenset[str] = frozenset()
) -> CheckFile:
    sources = [
        SourceCheck(source_id=source.id, url=source.url, fetched_at=CHECKED_AT, problem="HTTP 403")
        if source.id in unread
        else SourceCheck(
            source_id=source.id,
            url=source.url,
            route="LIVE",
            read_url=source.url,
            final_url=source.url,
            fetched_at=CHECKED_AT,
            content_type="text/plain",
            text_sha256=TEXT_SHA256,
            characters=100,
        )
        for source in dossier.sources
    ]
    quotes = [
        QuoteCheckEntry(
            claim_id=claim.id,
            source_id=quote.source_id,
            quote=quote.quote,
            result="FAIL" if claim.id in failing or quote.source_id in unread else "PASS",
        )
        for claim in dossier.claims
        for quote in claim.quotes
    ]
    return CheckFile(
        craft_slug=dossier.craft_slug,
        dossier_version=dossier.version,
        dossier_digest=verified_digest(dossier),
        checked_at=CHECKED_AT,
        tool=VERIFY_TOOL,
        sources=sources,
        quotes=quotes,
    )
