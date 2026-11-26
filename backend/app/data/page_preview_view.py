from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from .answer_kit import SCRIPT_HASH_SLOT, THEME_SLOT, script_hash, theme_css
from .contributor_kit import design_tokens
from .craft_master_loader import DATA_DIR
from .design_palette import THEMES, four_themes_css

__all__ = [
    "PAGE_PREVIEW_VIEW",
    "PAGE_PREVIEW_VIEW_PATH",
    "PAGE_PREVIEW_VIEW_URI",
    "STATUS_COLOURS",
    "page_preview_view",
    "status_css",
]

PAGE_PREVIEW_VIEW_PATH = DATA_DIR / "design" / "page-preview-view.html"
PAGE_PREVIEW_VIEW_URI = "ui://kalavigyan/page-preview.html"
PAGE_PREVIEW_VIEW = (
    PAGE_PREVIEW_VIEW_URI,
    "kalavigyan-page-preview",
    "A KalaVigyan page preview",
    "The MCP App that draws a page preview's report in KalaVigyan's design, from the preview result's "
    "structured data alone: the private link, each checklist rule with its verdict and evidence, how the page "
    "draws at 390 and 1440 px, what the craft's facts could show that the page does not draw, the agent's own "
    "design critique of its pictures and, when asked, the server's read of them (their count of notes on the "
    "card's line), coverage by field, "
    "figures, sources by grade, pictures by licence and one line of the page's counts beside Kutch Ajrakh's. Each "
    "card starts as one line and minimises back to it. It loads nothing from the network.",
)
STATUS_COLOURS = ("success", "success-wash", "error", "error-wash", "info", "info-wash")


@lru_cache(maxsize=1)
def page_preview_view() -> str:
    page = PAGE_PREVIEW_VIEW_PATH.read_bytes().decode("utf-8")
    tokens = json.loads(design_tokens())
    theme = theme_css(tokens) + status_css(tokens)
    return page.replace(THEME_SLOT, theme).replace(SCRIPT_HASH_SLOT, script_hash(page))


def status_css(tokens: Mapping[str, Any]) -> str:
    return four_themes_css({theme: _colours(tokens, theme) for theme in THEMES})


def _colours(tokens: Mapping[str, Any], theme: str) -> str:
    return "".join(
        f"{tokens['color'][name]['alias']}:{tokens['color'][name][theme]['hex']};" for name in STATUS_COLOURS
    )
