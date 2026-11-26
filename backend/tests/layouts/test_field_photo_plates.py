import dataclasses
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.api import mcp_field_photo_tools
from app.api.mcp_field_photo_tools import PLACE_STEP
from app.api.mcp_tools import ToolContext, answer
from app.research.component_specs import checked_spec
from app.research.page_layout import PageLayout, picture_label
from app.services import field_photo_plates
from app.services.craft_resolver import CraftIndexStore
from app.services.field_photo_plates import ClearedPhoto, field_key, field_plates, placed_photo_labels
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings
from app.services.monograph_generated_pictures import plate_spec
from app.services.open_work_subjects import WorkSubject

from .generated_parts import generated

IMAGE = uuid.UUID("5e1d0000-0001-4000-8000-0000000000f1")
OTHER = uuid.UUID("5e1d0000-0002-4000-8000-0000000000f2")
BAGH = WorkSubject(uuid.UUID(int=7), "craft", "Bagh-Print", "Bagh Print", gi=True)
TEXTILES = WorkSubject(uuid.UUID(int=8), "category", "Textiles", "Textiles", gi=False)
CREDIT = "Photo: Ramesh Khatri, via Field Repository"


def cleared(image: uuid.UUID) -> ClearedPhoto:
    key = field_key(image)
    return ClearedPhoto(
        image_id=image,
        key=key,
        label=picture_label("Bagh-Print", key),
        src=f"/api/field-voices/images/{image}",
        width=1600,
        height=1200,
        alt="A printer lays a block on the washed cloth",
        caption="Printing the first colour",
        credit=CREDIT,
        taken_on=date(2026, 3, 4),
    )


def layout(*entries: dict[str, Any]) -> PageLayout:
    return PageLayout.model_validate(
        {"subjectKind": "craft", "subjectSlug": "Bagh-Print", "version": 3, "entries": list(entries)}
    )


def offered(monkeypatch: pytest.MonkeyPatch, photos: list[ClearedPhoto]) -> list[WorkSubject]:
    asked: list[WorkSubject] = []

    async def listed(session: Any, subject: WorkSubject, **kwargs: Any) -> tuple[list[ClearedPhoto], int]:
        asked.append(subject)
        return photos, len(photos)

    monkeypatch.setattr(field_photo_plates, "cleared_photos", listed)
    monkeypatch.setattr(mcp_field_photo_tools, "cleared_photos", listed)
    return asked


def test_a_field_photograph_s_label_is_its_craft_s_picture_label_and_only_this_craft_s_are_placed() -> None:
    label = cleared(IMAGE).label
    assert label == f"bagh-print/pictures/field-{IMAGE.hex[:12]}"
    named = layout(
        {"ref": label, "chapter": "made", "order": 1, "role": "FIGURE"},
        {"ref": "bagh-print/pictures/i02", "chapter": "glance", "order": 1, "role": "PLATE"},
        {"ref": "dabu-print/pictures/field-0123456789ab", "chapter": "made", "order": 2, "role": "FIGURE"},
    )
    assert placed_photo_labels(BAGH, named) == {label}
    assert placed_photo_labels(TEXTILES, named) == set() and placed_photo_labels(BAGH, None) == set()


async def test_only_a_photograph_the_layout_names_is_drawn_where_it_places_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offered(monkeypatch, [cleared(IMAGE), cleared(OTHER)])
    entry = {
        "ref": cleared(IMAGE).label,
        "chapter": "made",
        "order": 4,
        "role": "FIGURE",
        "caption": "A new caption",
    }
    session: Any = None
    (plate,) = await field_plates(session, BAGH, layout(entry))
    assert (plate.key, plate.chapter, plate.role, plate.src) == (
        field_key(IMAGE),
        "made",
        "FIGURE",
        f"/api/field-voices/images/{IMAGE}",
    )
    assert plate.credit == CREDIT and plate.facts == ()
    assert await field_plates(session, BAGH, None) == []
    assert await field_plates(session, BAGH, layout()) == []


def test_a_field_photograph_is_a_picture_plate_the_page_may_draw_and_another_api_path_is_not() -> None:
    placed = layout({"ref": cleared(IMAGE).label, "chapter": "made", "order": 1, "role": "PLATE"})
    plate = field_photo_plates._plate(cleared(IMAGE), placed)
    built = plate_spec(plate, placed.entries[0], 0)
    assert built is not None
    spec, units = built
    assert spec["picture"]["src"] == f"/api/field-voices/images/{IMAGE}"
    assert [unit.nodes for unit in units.values()] == [["Printing the first colour"], [CREDIT]]
    stray = {**spec, "picture": {**spec["picture"], "src": f"/api/field-voices/audio/{IMAGE}"}}
    with pytest.raises(ValidationError):
        checked_spec("picture_plate", stray)


def test_a_field_photograph_placed_as_hero_is_the_masthead_with_its_credit(tmp_path: Path) -> None:
    photo = cleared(IMAGE)
    hero = layout({"ref": photo.label, "chapter": "glance", "order": 1, "role": "HERO"})
    plate = field_photo_plates._plate(photo, hero)
    built = assembled_document(
        dataclasses.replace(generated(), pictures=(plate,), layout=hero), Drawings(root=tmp_path)
    )
    assert built is not None
    opening = [(entry.kind, entry.ref) for entry in built.content.layout if entry.chapter == "opening"]
    assert opening[0] == ("component", photo.label)
    assert built.specs[photo.label]["picture"]["src"] == photo.src


async def test_the_agent_lists_the_craft_s_photographs_with_their_labels_and_how_to_place_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = offered(monkeypatch, [cleared(IMAGE)])

    async def subject(session: Any, kind: str, slug: str) -> WorkSubject:
        assert (kind, slug) == ("craft", "Bagh-Print")
        return BAGH

    monkeypatch.setattr(mcp_field_photo_tools, "subject_by_key", subject)
    no_session: Any = None
    tool_context = ToolContext(session=no_session, index=CraftIndexStore(), site="https://k.example")
    params = {"name": "list_field_photos", "arguments": {"craft_slug": "Bagh-Print"}}
    reply = await answer({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": params}, tool_context)
    assert reply is not None and reply["result"]["isError"] is False
    listed = reply["result"]["structuredContent"]
    assert asked == [BAGH] and listed["total"] == 1 and listed["nextStep"] == PLACE_STEP
    (photo,) = listed["photos"]
    assert (photo["label"], photo["credit"], photo["takenOn"]) == (cleared(IMAGE).label, CREDIT, "2026-03-04")
