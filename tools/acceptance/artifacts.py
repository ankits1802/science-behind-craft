from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from atomic_write import write_text_atomically

from .costs import CACHE_READ_FACTOR, CACHE_WRITE_FACTOR, Prices
from .loop import LoopOutcome, Turn
from .pictures import Picture
from .spend import ToolSpend
from .transcript import RunFacts, transcript

__all__ = [
    "COST_FILE",
    "OPINION_FILE",
    "PICTURES_DIR",
    "PREVIEW_FILE",
    "PREVIEW_URL_FILE",
    "SUMMARY_FILE",
    "TRANSCRIPT_FILE",
    "Spend",
    "cost_record",
    "write_cost",
    "write_json",
    "write_pictures",
    "write_preview_urls",
    "write_transcript",
]

TRANSCRIPT_FILE = "transcript.json"
PREVIEW_FILE = "preview.json"
PREVIEW_URL_FILE = "preview-url.txt"
COST_FILE = "cost.json"
SUMMARY_FILE = "summary.md"
OPINION_FILE = "opinion.md"
PICTURES_DIR = "pictures"
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


@dataclass(frozen=True)
class Spend:
    facts: RunFacts
    prices: Prices
    turns: Sequence[Turn]
    loop_usd: Decimal
    opinion_usd: Decimal = Decimal(0)
    tools: Sequence[ToolSpend] = ()


def write_json(path: Path, data: Any) -> None:
    write_text_atomically(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_transcript(out: Path, facts: RunFacts, outcome: LoopOutcome) -> None:
    write_json(out / TRANSCRIPT_FILE, transcript(facts, outcome))


def cost_record(spend: Spend) -> dict[str, Any]:
    usage = {
        name: sum(int((turn.message.get("usage") or {}).get(name) or 0) for turn in spend.turns)
        for name in USAGE_FIELDS
    }
    return {
        "model": spend.facts.model,
        "capUsd": spend.facts.cap_usd,
        "spentUsd": str(spend.loop_usd + spend.opinion_usd),
        "loopUsd": str(spend.loop_usd),
        "opinionUsd": str(spend.opinion_usd),
        "turns": len(spend.turns),
        "usage": usage,
        "pricePerMTok": {
            "input": str(spend.prices.input_per_mtok),
            "output": str(spend.prices.output_per_mtok),
        },
        "cacheWriteFactor": str(CACHE_WRITE_FACTOR),
        "cacheReadFactor": str(CACHE_READ_FACTOR),
        "byTool": [
            {
                "tool": row.name,
                "calls": row.calls,
                "errors": row.errors,
                "resultChars": row.result_chars,
                "argumentChars": row.argument_chars,
                "estimatedTokens": row.tokens,
                "estimatedUsd": str(row.usd),
            }
            for row in spend.tools
        ],
    }


def write_cost(out: Path, spend: Spend) -> None:
    write_json(out / COST_FILE, cost_record(spend))


def write_pictures(out: Path, pictures: Sequence[Picture]) -> list[tuple[str, str]]:
    folder = out / PICTURES_DIR
    folder.mkdir(parents=True, exist_ok=True)
    for picture in pictures:
        (folder / picture.name).write_bytes(picture.data)
    return [(f"{PICTURES_DIR}/{picture.name}", picture.caption) for picture in pictures]


def write_preview_urls(out: Path, urls: Sequence[tuple[str, str | None]]) -> None:
    lines = [f"{label}: {url}" for label, url in urls if url]
    write_text_atomically(out / PREVIEW_URL_FILE, "\n".join(lines or ["no preview was made"]) + "\n")
