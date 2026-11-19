import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope
from app.services.knowledge_export import craft_export, exported_slugs


async def run(out: Path, slugs: list[str]) -> dict[str, Any]:
    site = get_settings().public_web_url.rstrip("/")
    now = datetime.now(UTC)
    written: list[str] = []
    try:
        async with session_scope() as session:
            for slug in slugs or await exported_slugs(session):
                exported = await craft_export(session, slug, site=site, now=now)
                body = json.dumps(
                    exported.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=1
                )
                (out / f"{slug}.json").write_text(body + "\n", encoding="utf-8", newline="\n")
                written.append(slug)
    finally:
        await dispose_engine()
    return {"exportedAt": now.isoformat(), "out": str(out), "crafts": written}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export_knowledge")
    parser.add_argument(
        "--out", type=Path, required=True, help="an existing folder for one JSON file per craft"
    )
    parser.add_argument(
        "--craft", action="append", default=[], help="a craft slug; repeat it, or omit for all"
    )
    args = parser.parse_args(argv)
    if not args.out.is_dir():
        parser.error(f"{args.out} is not a folder")
    print(json.dumps(asyncio.run(run(args.out, args.craft))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
