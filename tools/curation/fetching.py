from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .commons import PictureFailed, commons_picture, picture_lines
from .output import utf8_console, write_text_atomically
from .polite import PoliteHttp
from .reading import ReadFailed, SourceText, read_source
from .wayback import SNAPSHOT

__all__ = ["SEPARATOR", "main", "rendered"]

SEPARATOR = "-" * 40


def rendered(reading: SourceText) -> list[str]:
    lines = reading.lines
    header = [
        f"url: {reading.url}",
        f"read: {reading.route} {reading.read_url}",
        f"final url: {reading.final_url}",
        f"content type: {reading.content_type}",
        f"fetched at: {reading.fetched_at.isoformat()}",
        f"text sha256: {reading.sha256}",
        f"lines: {len(lines)}{' (truncated)' if reading.truncated else ''}",
    ]
    if reading.route == "ARCHIVE":
        header.append(f"archivedUrl: {reading.read_url}")
    width = len(str(len(lines)))
    return [*header, SEPARATOR, *(f"{number:>{width}}  {line}" for number, line in enumerate(lines, start=1))]


def main(argv: Sequence[str] | None = None) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(
        description="Fetch a source as the verifier reads it and show its text with line numbers."
    )
    parser.add_argument("url", help="an https URL, or a Wayback Machine snapshot URL")
    parser.add_argument("--out", type=Path, help="save the text to this file instead of printing it")
    parser.add_argument(
        "--picture",
        action="store_true",
        help="read a Wikimedia Commons file page's size and credit (imageinfo) instead of a source's text",
    )
    options = parser.parse_args(argv)
    if not (options.url.startswith("https://") or SNAPSHOT.match(options.url)):
        print(f"{options.url}: a dossier cites https URLs only", file=sys.stderr)
        return 1
    with PoliteHttp() as http:
        try:
            lines = (
                _picture(http, options.url) if options.picture else rendered(read_source(http, options.url))
            )
        except ReadFailed as failure:
            print(f"could not read {failure.url}: {'; '.join(failure.reasons)}", file=sys.stderr)
            return 1
        except PictureFailed as failure:
            print(str(failure), file=sys.stderr)
            return 1
    text = "\n".join(lines) + "\n"
    if options.out is None:
        sys.stdout.write(text)
    else:
        write_text_atomically(options.out, text)
        print(f"wrote {len(lines)} lines to {options.out}", file=sys.stderr)
    return 0


def _picture(http: PoliteHttp, page_url: str) -> list[str]:
    return picture_lines(commons_picture(http, page_url))
