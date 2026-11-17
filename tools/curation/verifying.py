from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

from app.curation.check_file import (
    VERIFY_TOOL,
    CheckFile,
    QuoteCheckEntry,
    SourceCheck,
    check_file_text,
    verified_digest,
)
from app.curation.dossier import Dossier, parse_dossier
from app.curation.files import check_path
from app.curation.matching import match_key, quote_found
from app.curation.parts import Source
from app.curation.problems import schema_problems
from pydantic import ValidationError

from .output import relative_label, utf8_console, write_text_atomically
from .polite import PoliteHttp
from .reading import ReadFailed, SourceText, read_source

__all__ = ["READ_WORKERS", "failure_lines", "main", "read_sources", "verify_dossier", "verify_file"]

READ_WORKERS = 4
QUOTE_SHOWN_CHARS = 80

Reader = Callable[[Source], SourceText]
Reading = SourceText | ReadFailed


def verify_dossier(
    dossier: Dossier, read: Reader, *, now: Callable[[], datetime] = partial(datetime.now, UTC)
) -> CheckFile:
    readings = read_sources(dossier.sources, read)
    keys = {
        source_id: match_key(found.text)
        for source_id, found in readings.items()
        if isinstance(found, SourceText)
    }
    quotes = [
        QuoteCheckEntry(
            claim_id=claim.id,
            source_id=quote.source_id,
            quote=quote.quote,
            result="PASS"
            if quote.source_id in keys and quote_found(quote.quote, keys[quote.source_id])
            else "FAIL",
        )
        for claim in dossier.claims
        for quote in claim.quotes
    ]
    return CheckFile(
        craft_slug=dossier.craft_slug,
        dossier_version=dossier.version,
        dossier_digest=verified_digest(dossier),
        checked_at=now(),
        tool=VERIFY_TOOL,
        sources=[_source_check(source, readings[source.id], now) for source in dossier.sources],
        quotes=quotes,
    )


def read_sources(
    sources: Sequence[Source], read: Reader, *, workers: int = READ_WORKERS
) -> dict[str, Reading]:
    by_host: dict[str, list[Source]] = {}
    for source in sources:
        by_host.setdefault((urlsplit(source.url).hostname or "").casefold(), []).append(source)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        groups = list(pool.map(partial(_read_group, read), by_host.values()))
    return {source_id: reading for group in groups for source_id, reading in group}


def failure_lines(label: str, check: CheckFile) -> list[str]:
    unread = {source.source_id for source in check.sources if not source.read}
    lines = [
        f"{label}: {source.source_id}: could not be read: {source.problem}"
        for source in check.sources
        if source.source_id in unread
    ]
    lines += [
        f"{label}: {entry.claim_id}: quote not found in {entry.source_id}: {entry.quote[:QUOTE_SHOWN_CHARS]!r}"
        for entry in check.quotes
        if entry.result == "FAIL" and entry.source_id not in unread
    ]
    return lines


def verify_file(path: Path, read: Reader) -> tuple[list[str], CheckFile | None]:
    label = relative_label(path)
    try:
        dossier = parse_dossier(path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError:
        return [f"{label}: file: is not UTF-8 text"], None
    except ValidationError as error:
        return [problem.line(label) for problem in schema_problems(error)], None
    check = verify_dossier(dossier, read)
    write_text_atomically(check_path(path, dossier.craft_slug), check_file_text(check))
    return failure_lines(label, check), check


def main(argv: Sequence[str] | None = None) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(
        description="Re-fetch every source of each dossier, check every quote, write <CraftSlug>.check.json."
    )
    parser.add_argument("dossiers", nargs="+", type=Path, help="dossier files to verify")
    options = parser.parse_args(argv)
    failed = False
    with PoliteHttp() as http:
        read = partial(_read_with, http)
        for path in options.dossiers:
            lines, check = verify_file(path, read)
            for line in lines:
                print(line)
            failed = failed or bool(lines)
            if check is not None:
                print(_summary(relative_label(path), check), file=sys.stderr)
    return 1 if failed else 0


def _read_with(http: PoliteHttp, source: Source) -> SourceText:
    return read_source(http, source.url, archived_url=source.archived_url)


def _read_group(read: Reader, group: list[Source]) -> list[tuple[str, Reading]]:
    return [(source.id, _attempt(read, source)) for source in group]


def _attempt(read: Reader, source: Source) -> Reading:
    try:
        return read(source)
    except ReadFailed as failure:
        return failure


def _source_check(source: Source, reading: Reading, now: Callable[[], datetime]) -> SourceCheck:
    if isinstance(reading, ReadFailed):
        return SourceCheck(
            source_id=source.id, url=source.url, fetched_at=now(), problem="; ".join(reading.reasons)
        )
    return SourceCheck(
        source_id=source.id,
        url=source.url,
        route=reading.route,
        read_url=reading.read_url,
        final_url=reading.final_url,
        fetched_at=reading.fetched_at,
        content_type=reading.content_type,
        text_sha256=reading.sha256,
        characters=len(reading.text),
        truncated=reading.truncated,
    )


def _summary(label: str, check: CheckFile) -> str:
    read = sum(1 for source in check.sources if source.read)
    passed = sum(1 for entry in check.quotes if entry.result == "PASS")
    return (
        f"{label}: {read} of {len(check.sources)} sources read, {passed} of {len(check.quotes)} quotes passed; "
        f"wrote {check.craft_slug}.check.json"
    )
