from __future__ import annotations

import re
from functools import lru_cache

from .craft_master_loader import DATA_DIR

__all__ = [
    "CONTRIBUTOR_SKILL_PATH",
    "DESIGN_TOKENS_PATH",
    "SITE_SKILL_PATH",
    "contributor_skill",
    "design_tokens",
    "skill_section",
]

CONTRIBUTOR_SKILL_PATH = DATA_DIR / "contributor" / "SKILL.md"
DESIGN_TOKENS_PATH = DATA_DIR / "design" / "tokens.json"
SITE_SKILL_PATH = "/skills/kalavigyan-contributor/SKILL.md"
SECTION_HEADING = re.compile(r"^## (?P<title>.+)$", re.MULTILINE)


@lru_cache(maxsize=1)
def contributor_skill() -> str:
    return CONTRIBUTOR_SKILL_PATH.read_bytes().decode("utf-8")


@lru_cache(maxsize=1)
def design_tokens() -> str:
    return DESIGN_TOKENS_PATH.read_bytes().decode("utf-8")


def skill_section(title: str) -> str:
    text = contributor_skill()
    headings = list(SECTION_HEADING.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group("title") == title:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            return text[heading.start() : end].strip()
    raise KeyError(f"the contributor skill has no section {title!r}")
