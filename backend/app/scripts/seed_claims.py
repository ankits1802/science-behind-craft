import argparse
import asyncio
import json
from typing import Any

from app.services.claim_seed import claim_seed_plan, load_seed_claims


async def run() -> dict[str, Any]:
    from app.core.db import dispose_engine, session_scope
    from app.services.claim_seed import seed_claims

    try:
        async with session_scope() as session:
            return await seed_claims(session)
    finally:
        await dispose_engine()


def dry_run() -> dict[str, Any]:
    plan = claim_seed_plan(load_seed_claims())
    return {"total": {key: len(rows) for key, rows in plan.items()}, "dryRun": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed_claims")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = dry_run() if args.dry_run else asyncio.run(run())
    print(json.dumps(result))
    if result.get("unresolvedSlugs"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
