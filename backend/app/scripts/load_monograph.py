import argparse
import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from app.core.db import dispose_engine, session_scope
from app.scripts.build_monograph import SERVED_FOLDERS, monograph_content
from app.services.monograph_load import load_monograph


async def run(slugs: list[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    try:
        async with session_scope() as session:
            for slug in slugs:
                loaded = await load_monograph(session, monograph_content(slug), now=datetime.now(UTC))
                reports.append(loaded.as_dict())
    finally:
        await dispose_engine()
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="load_monograph")
    parser.add_argument("--craft", choices=sorted(SERVED_FOLDERS), help="load one monograph, not every one")
    args = parser.parse_args(argv)
    print(json.dumps(asyncio.run(run([args.craft] if args.craft else sorted(SERVED_FOLDERS)))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
