from __future__ import annotations

import json
from functools import lru_cache

from .answer_kit import SCRIPT_HASH_SLOT, THEME_SLOT, script_hash, theme_css
from .contributor_kit import design_tokens
from .craft_master_loader import DATA_DIR

__all__ = ["PAGE_REVIEW_VIEW", "PAGE_REVIEW_VIEW_PATH", "PAGE_REVIEW_VIEW_URI", "page_review_view"]

PAGE_REVIEW_VIEW_PATH = DATA_DIR / "design" / "page-review-view.html"
PAGE_REVIEW_VIEW_URI = "ui://kalavigyan/page-review.html"
PAGE_REVIEW_VIEW = (
    PAGE_REVIEW_VIEW_URI,
    "kalavigyan-page-review",
    "A KalaVigyan page proposal under review",
    "The MCP App that draws review_queue's page proposals in KalaVigyan's design, from the result's "
    "structured data alone: the page as it stands and as it will be, chapter by chapter, each sentence, "
    "component and picture marked added, changed or removed, each part with its state, and the decisions "
    "made so far. It starts as one line and minimises back to it. It loads nothing from the network.",
)


@lru_cache(maxsize=1)
def page_review_view() -> str:
    page = PAGE_REVIEW_VIEW_PATH.read_bytes().decode("utf-8")
    theme = theme_css(json.loads(design_tokens()))
    return page.replace(THEME_SLOT, theme).replace(SCRIPT_HASH_SLOT, script_hash(page))
