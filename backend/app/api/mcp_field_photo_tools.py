from __future__ import annotations

from datetime import date

from pydantic import Field

from app.research.base import ContractModel
from app.research.crafts import SLUG_MAX_CHARS
from app.services.field_photo_plates import ClearedPhoto, cleared_photos
from app.services.open_work_subjects import subject_by_key

from .mcp_tool_base import PICTURES, Arguments, Tool, ToolContext

__all__ = ["DESCRIPTION", "FIELD_PHOTO_TOOLS", "PLACE_STEP", "FieldPhotos", "ListFieldPhotos"]

CRAFT = "craft"
LIMIT_DEFAULT = 20
LIMIT_MAX = 50
DESCRIPTION = (
    "Lists the field photographs from KalaVigyan's field portals that a craft's page may show: only those "
    "already published on the craft's page, never an artisan's identity photograph. Each comes with its label, "
    "caption, alt text, credit and size. A page's layout entry places one by its label, with its chapter, "
    "order and role (HERO for the masthead, OPENER, PLATE or FIGURE) and optionally a size, crop or caption. "
    "The site draws it with its credit as listed."
)
PLACE_STEP = (
    "Place a photograph by its label in the page's layout, where its chapter's story needs it; a page shows "
    "each picture once."
)
LISTED = "{shown} of {total} field photographs of {slug} the page may show."


class ListFieldPhotos(Arguments):
    craft_slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS, description="The craft's slug")
    offset: int = Field(default=0, ge=0, description="Photographs to skip, for the next page of the list")
    limit: int = Field(default=LIMIT_DEFAULT, ge=1, le=LIMIT_MAX)


class FieldPhoto(ContractModel):
    label: str
    caption: str
    alt: str
    credit: str
    width: int
    height: int
    taken_on: date | None


class FieldPhotos(ContractModel):
    craft_slug: str
    photos: list[FieldPhoto]
    total: int
    next_offset: int | None
    message: str
    next_step: str


async def _list_field_photos(context: ToolContext, arguments: ListFieldPhotos) -> FieldPhotos:
    subject = await subject_by_key(context.session, CRAFT, arguments.craft_slug)
    photos, total = await cleared_photos(
        context.session, subject, limit=arguments.limit, offset=arguments.offset
    )
    following = arguments.offset + len(photos)
    return FieldPhotos(
        craft_slug=subject.slug,
        photos=[_listed(photo) for photo in photos],
        total=total,
        next_offset=following if following < total else None,
        message=LISTED.format(shown=len(photos), total=total, slug=subject.slug),
        next_step=PLACE_STEP,
    )


def _listed(photo: ClearedPhoto) -> FieldPhoto:
    return FieldPhoto(
        label=photo.label,
        caption=photo.caption,
        alt=photo.alt,
        credit=photo.credit,
        width=photo.width,
        height=photo.height,
        taken_on=photo.taken_on,
    )


FIELD_PHOTO_TOOLS: tuple[Tool, ...] = (
    Tool(
        "list_field_photos",
        "List a craft's field photographs",
        DESCRIPTION,
        ListFieldPhotos,
        FieldPhotos,
        _list_field_photos,
        group=PICTURES,
    ),
)
