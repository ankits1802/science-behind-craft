from __future__ import annotations

from collections.abc import Sequence

from app.core.errors import InvalidInput
from app.research.craft_page import CraftPage
from app.research.crafts import CraftRef
from app.science.records import ProcessRecords

from .chapter_preview import preview_rows
from .craft_page import craft_page
from .craft_page_records import CraftPageRecords, page_craft
from .craft_page_register import register_context
from .curation_preview import dossier_records, master_craft
from .knowledge_view import craft_ref

__all__ = ["register_page", "register_records"]


def register_page(craft_slug: str, *, dossiers: Sequence[str] = (), family: str | None = None) -> CraftPage:
    records = register_records(craft_slug, dossiers=dossiers)
    return craft_page(records, preview_rows(records, family=family, inputs=None))


def register_records(craft_slug: str, *, dossiers: Sequence[str] = ()) -> CraftPageRecords:
    if craft_slug in dossiers:
        raise InvalidInput(
            f"{craft_slug} is previewed from the register alone, so its own dossier is not held"
        )
    craft, names = master_craft(craft_slug)
    ref = CraftRef.model_validate(craft_ref(craft))
    records = CraftPageRecords(
        craft=page_craft(craft, names),
        curated=None,
        views=(),
        facts={},
        sources={},
        process=ProcessRecords(ref, (), (), (), (), (), {}, {}),
    )
    held = {slug: dossier_records(slug) for slug in dossiers}
    return register_context(records, None, held)
