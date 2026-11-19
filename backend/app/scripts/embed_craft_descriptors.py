import argparse
import asyncio
import json
from typing import Any

from app.core.db import dispose_engine, session_scope
from app.core.errors import AppError
from app.providers.embedding import router_embedder
from app.retrieval.deadline import Deadline
from app.services.craft_resolver import fill_descriptor_embeddings


async def run(seconds: float | None) -> dict[str, Any]:
    deadline = Deadline.after(seconds) if seconds is not None else None
    try:
        async with session_scope() as session:
            filled = await fill_descriptor_embeddings(session, router_embedder(), deadline=deadline)
    except AppError as error:
        return {"ok": False, "error": str(error)}
    finally:
        await dispose_engine()
    return {"ok": True, "filled": filled}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="embed_craft_descriptors")
    parser.add_argument(
        "--seconds", type=float, help="stop starting new batches after this many seconds; the rest waits"
    )
    args = parser.parse_args(argv)
    report = asyncio.run(run(args.seconds))
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
