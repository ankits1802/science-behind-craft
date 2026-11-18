from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.curation.checks import CheckContext, default_context
from app.curation.files import (
    CURATION_DIR,
    INDEX_NAME,
    category_paths,
    checked_dossier,
    dossier_paths,
    stray_problems,
)
from app.curation.index import curation_index, index_text

from .output import relative_label, utf8_console, write_text_atomically

__all__ = ["CheckRun", "check_run", "main", "stale_index_lines", "write_index"]

INDEX_STALE = "is not current; run python tools/curation/check.py --write-index and keep the file it writes"


@dataclass(frozen=True)
class CheckRun:
    lines: list[str]
    index: str


def check_run(targets: Sequence[Path], directory: Path, context: CheckContext) -> CheckRun:
    listed = dossier_paths(directory) if directory.is_dir() else []
    categories = category_paths(directory) if directory.is_dir() else []
    missing = [path for path in targets if not path.is_file()]
    present = [path for path in targets if path.is_file()]
    results = {path.resolve(): checked_dossier(path, context) for path in [*listed, *categories, *present]}
    wanted = present if targets else [*listed, *categories]
    lines = [f"{relative_label(path)}: file: does not exist" for path in missing]
    lines += [
        problem.line(relative_label(path)) for path in wanted for problem in results[path.resolve()].problems
    ]
    if not targets and directory.is_dir():
        lines += [problem.line(relative_label(directory)) for problem in stray_problems(directory)]
    index = index_text(
        curation_index(
            [results[path.resolve()] for path in listed], [results[path.resolve()] for path in categories]
        )
    )
    return CheckRun(lines, index)


def stale_index_lines(directory: Path, index: str) -> list[str]:
    index_path = directory / INDEX_NAME
    current = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    return [] if current == index else [f"{relative_label(index_path)}: index: {INDEX_STALE}"]


def write_index(directory: Path, index: str) -> None:
    if directory.is_dir():
        write_text_atomically(directory / INDEX_NAME, index)


def main(argv: Sequence[str] | None = None) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(
        description="Offline checks of curated dossiers (plan section 6); writes nothing unless --write-index."
    )
    parser.add_argument("dossiers", nargs="*", type=Path, help="dossiers to check (default: every dossier)")
    parser.add_argument("--dir", type=Path, default=CURATION_DIR, help="the curation directory")
    index = parser.add_mutually_exclusive_group()
    index.add_argument("--check-index", action="store_true", help="report a stale index.json (CI)")
    index.add_argument(
        "--write-index", action="store_true", help="regenerate index.json from every dossier (once per batch)"
    )
    options = parser.parse_args(argv)
    outcome = check_run(options.dossiers, options.dir, default_context())
    lines = list(outcome.lines)
    if options.check_index:
        lines += stale_index_lines(options.dir, outcome.index)
    if options.write_index:
        write_index(options.dir, outcome.index)
    for line in lines:
        print(line)
    return 1 if lines else 0
