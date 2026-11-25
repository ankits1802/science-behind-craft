from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_families import load_craft_families
from app.data.craft_master_loader import ALL_INDIA
from app.data.english_words import load_english_words
from app.models import Craft
from app.research.image_relevance import PictureContext, picture_context

from .craft_page_family import family_names, family_place
from .craft_resolver import alias_names, craft_places
from .knowledge_view import resolve_craft

__all__ = ["any_craft_context", "craft_picture_context", "picture_context_of"]


async def craft_picture_context(session: AsyncSession, craft_slug: str | None) -> PictureContext:
    craft = await resolve_craft(session, craft_slug) if craft_slug else None
    if craft is None:
        return any_craft_context()
    return await picture_context_of(session, craft)


async def picture_context_of(session: AsyncSession, craft: Craft) -> PictureContext:
    aliases = (await alias_names(session, [craft.id])).get(craft.id, [])
    located = (await craft_places(session, [craft.id])).get(craft.id, [])
    category, kind = await family_names(session, craft) or (craft.category, None)
    family = family_place(category, kind).family
    return picture_context(
        [craft.name, *([craft.localName] if craft.localName else []), *aliases],
        _places(craft, located),
        family.picture_words if family is not None else load_craft_families().picture_words,
        ordinary=load_english_words(),
    )


def any_craft_context() -> PictureContext:
    return picture_context((), (), load_craft_families().picture_words, ordinary=load_english_words())


def _places(craft: Craft, located: list[str]) -> list[str]:
    stated = [*(craft.stateOfOrigin or ()), *(craft.stateOfPractice or ()), *located]
    return [place for place in stated if place != ALL_INDIA]
