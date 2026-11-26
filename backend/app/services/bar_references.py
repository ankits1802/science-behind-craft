from __future__ import annotations

from functools import cache

from app.research.bar_references import KIT_GUIDES, WorkedPage, kit_page, worked_chapter, worked_topic
from app.research.page_counts import BAR_SLUG

from .monograph_document import component_specs, kit_sources, monograph_content
from .page_layouts import page_path

__all__ = ["kit_text", "worked_chapters", "worked_page", "worked_text", "worked_topics"]


@cache
def worked_page() -> WorkedPage:
    content = monograph_content(BAR_SLUG)
    return WorkedPage(content=content, specs=component_specs(content), path=page_path("craft", BAR_SLUG))


def worked_chapters() -> tuple[str, ...]:
    return tuple(chapter.key for chapter in worked_page().chapters())


def worked_topics() -> tuple[str, ...]:
    return tuple(worked_topic(chapter) for chapter in worked_chapters())


@cache
def worked_text(chapter: str) -> str:
    return worked_chapter(worked_page(), chapter)


@cache
def kit_text(topic: str) -> str:
    guide = KIT_GUIDES[topic]
    return kit_page(guide, kit_sources()[guide.file])
