import argparse
import asyncio
import json
from typing import Any

from app.services.district_seed import district_seed_plan


async def run() -> dict[str, Any]:
    from app.core.db import dispose_engine, session_scope
    from app.services.district_seed import seed_districts

    try:
        async with session_scope() as session:
            return await seed_districts(session)
    finally:
        await dispose_engine()


def dry_run() -> dict[str, Any]:
    plan = district_seed_plan()
    return {
        "states": len(plan["states"]),
        "districts": len(plan["districts"]),
        "districtsWithShape": sum(1 for row in plan["districts"] if row["lines"]),
        "dryRun": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed_districts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(dry_run() if args.dry_run else asyncio.run(run())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
