import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.db import dispose_engine, session_scope
from app.research.craft_page import craft_page_text
from app.services.curation_import import import_curation
from app.services.curation_preview import dossier_preview


async def run() -> dict[str, Any]:
    try:
        async with session_scope() as session:
            report = await import_curation(session)
            return report.summary()
    finally:
        await dispose_engine()


def preview(craft_slug: str, out: Path) -> dict[str, Any]:
    page = dossier_preview(craft_slug)
    out.write_text(craft_page_text(page), encoding="utf-8", newline="\n")
    return {"preview": craft_slug, "out": str(out), "claims": len(page.claims)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="import_curation")
    parser.add_argument(
        "--preview", metavar="CRAFT_SLUG", help="write a dossier's craft page without a database"
    )
    parser.add_argument("--out", type=Path, help="where --preview writes the page JSON")
    args = parser.parse_args(argv)
    if args.preview:
        if args.out is None:
            parser.error("--preview needs --out")
        print(json.dumps(preview(args.preview, args.out)))
        return 0
    result = asyncio.run(run())
    print(json.dumps(result))
    return 2 if result["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
