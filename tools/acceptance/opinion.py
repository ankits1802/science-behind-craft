from __future__ import annotations

import base64
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from .preview import Picture
from .request import EFFORT

__all__ = [
    "DESIGN_SKILL",
    "OPINION_MAX_TOKENS",
    "OPINION_RESERVE_USD",
    "design_principles",
    "opinion_params",
    "opinion_text",
]

DESIGN_SKILL = Path(".claude/skills/kalavigyan-design/SKILL.md")
PRINCIPLES_START = "## 1. Principles"
PRINCIPLES_END = "## 3. "
OPINION_MAX_TOKENS = 16_000
OPINION_RESERVE_USD = Decimal(1)
OPINION_SYSTEM = (
    "You give a second opinion on how a web page looks. You are shown pictures of one page and a design "
    "system's principles and non-negotiables. Judge only what the pictures show; your opinion decides nothing."
)
OPINION_ASK = (
    "Rate the page in these pictures against each principle and each non-negotiable above. For each, say "
    "whether the page meets it, misses it or cannot be judged from the pictures, with the reason you see. "
    "End with a rating out of 10 and the three changes that would help the page most."
)


def design_principles(skill_text: str) -> str:
    start = skill_text.find(PRINCIPLES_START)
    end = skill_text.find(PRINCIPLES_END, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        raise ValueError(f"{DESIGN_SKILL} has no '{PRINCIPLES_START}' section followed by '{PRINCIPLES_END}'")
    return skill_text[start:end].strip()


def opinion_params(model: str, principles: str, pictures: Sequence[Picture]) -> dict[str, Any]:
    if not pictures:
        raise ValueError("a second opinion needs at least one picture of the page")
    content: list[dict[str, Any]] = [{"type": "text", "text": principles}]
    for picture in pictures:
        content.append({"type": "text", "text": picture.caption or picture.name})
        content.append({"type": "image", "source": _image_source(picture)})
    content.append({"type": "text", "text": OPINION_ASK})
    return {
        "model": model,
        "max_tokens": OPINION_MAX_TOKENS,
        "system": OPINION_SYSTEM,
        "messages": [{"role": "user", "content": content}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": EFFORT},
    }


def opinion_text(message: dict[str, Any]) -> str:
    texts = [block.get("text", "") for block in message.get("content") or [] if block.get("type") == "text"]
    return "\n\n".join(text.strip() for text in texts if text.strip())


def _image_source(picture: Picture) -> dict[str, str]:
    data = base64.b64encode(picture.data).decode("ascii")
    return {"type": "base64", "media_type": picture.mime, "data": data}
