import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.db import dispose_engine, session_scope
from app.services.dossier_export import CHANGED, DOSSIER_DIR, NEW, ExportRun, export_dossiers

DIFF_FOUND = 1
REFUSED = 2


async def run(slugs: list[str], git: Path) -> ExportRun:
    try:
        async with session_scope() as session:
            return await export_dossiers(session, slugs, directory=git)
    finally:
        await dispose_engine()


def write_exports(found: ExportRun, out: Path) -> list[str]:
    written = []
    for export in found.exports:
        path = out / export.file
        if path.is_file() and path.read_text(encoding="utf-8") == export.text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(export.text, encoding="utf-8", newline="\n")
        written.append(export.file)
    return written


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export_dossiers",
        description="Export the curated dossiers the database holds, in the schema the import reads.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--diff", action="store_true", help="report what differs from the dossiers in git")
    mode.add_argument("--out", type=Path, help="a folder to write the exported dossiers into")
    parser.add_argument(
        "--slug", action="append", default=[], help="a craft or category slug; repeat it, or omit for all"
    )
    parser.add_argument(
        "--git",
        type=Path,
        default=DOSSIER_DIR,
        help="the folder of dossiers to compare with and keep the layout of",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    found = asyncio.run(run(args.slug, args.git))
    result: dict[str, Any] = {"exportedAt": datetime.now(UTC).isoformat(), **found.summary()}
    if args.out is not None:
        result["written"] = write_exports(found, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if found.refused:
        return REFUSED
    differs = any(export.status in (CHANGED, NEW) for export in found.exports)
    return DIFF_FOUND if args.diff and differs else 0


if __name__ == "__main__":
    raise SystemExit(main())
