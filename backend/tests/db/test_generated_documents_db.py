from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import User
from app.research.page_layout import LayoutWrite
from app.services.monograph_generated import generated_document, generated_parts
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings
from app.services.open_work_subjects import subject_by_key
from app.services.page_layouts import write_layout

from .page_documents_seed import (
    ADMIN,
    ALUM,
    BARE_SLUG,
    CATEGORY_SLUG,
    CONCEPT_PLAYER,
    CRAFT_PLAYER,
    CRAFT_SLUG,
    CRAFT_TEXT,
    FAMILY_SLUG,
    OTHER_CRAFTS_PLAYER,
    PICTURE,
    seed,
)
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

MASTHEAD = [
    "masthead-kicker",
    "masthead-title",
    "label-place-term",
    "label-place",
    "label-gi-term",
    "label-gi",
]


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


def texts(document: object) -> list[str]:
    return [str(unit.nodes) for unit in document.content.units.values()]


def plate_units(document: object, label: str) -> list[str]:
    figure = document.specs[label]["figure"]
    return [caption["unit"] for caption in figure["captions"]] + [figure["credit"]]


async def test_a_seeded_craft_reads_its_published_section_sources_masthead_and_picture(
    session: AsyncSession,
) -> None:
    document = await generated_document(session, "craft", CRAFT_SLUG)
    assert document is not None
    assert (document.subject_kind, document.subject_slug, document.title, document.version) == (
        "craft",
        CRAFT_SLUG,
        "Page Docs Test Craft",
        3,
    )
    assert any("Alum fixes the madder red on the" in text for text in texts(document))
    assert not any("proposed history" in text for text in texts(document))
    assert [(key, s.number, s.title) for key, s in document.content.sources.items()] == [
        ("g1", 1, "Alum mordants on cotton")
    ]
    held = plate_units(document, PICTURE)
    assert [
        (e.chapter, e.ref, e.within) for e in document.content.layout[: 1 + len(held) + len(MASTHEAD)]
    ] == [
        ("opening", PICTURE, None),
        *[("opening", unit, PICTURE) for unit in held],
        *[("opening", unit, None) for unit in MASTHEAD],
    ]
    titles = [
        document.content.units[e.ref].nodes for e in document.content.layout if e.ref.startswith("chapter-")
    ]
    assert titles == [["How it is made"], ["The chemistry"], ["Why Madhya Pradesh"], ["Sources"]]
    units = document.content.units
    assert (units["label-place"].nodes, units["label-gi"].nodes) == (
        ["Madhya Pradesh"],
        ["Registered geographical indication"],
    )
    assert document.specs[PICTURE]["setting"] == "figure"
    assert document.specs[PICTURE]["picture"]["focal"] == {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.6}
    assert document.page_url.endswith(f"/crafts/{CRAFT_SLUG}")


async def test_the_craft_brings_its_own_and_its_concepts_shared_components_and_draws_the_one_with_a_spec(
    session: AsyncSession, tmp_path: Path
) -> None:
    parts = await generated_parts(session, await subject_by_key(session, "craft", CRAFT_SLUG))
    assert parts is not None
    assert [(c.label, c.monograph, c.anchor, c.subjects) for c in parts.components] == [
        (CRAFT_PLAYER, "Page-Docs-Monograph", "#fig2", ()),
        (CONCEPT_PLAYER, "Page-Docs-Monograph", "#fig2", (f"concept:{ALUM}",)),
    ]
    assert OTHER_CRAFTS_PLAYER not in {c.label for c in parts.components}
    specs = tmp_path / "Page-Docs-Monograph" / "specs"
    specs.mkdir(parents=True)
    (specs / "page-docs-test-craft__chemistry__alum-player.json").write_text(
        '{"bath": "alum"}', encoding="utf-8"
    )
    document = assembled_document(parts, Drawings(root=tmp_path))
    assert document is not None
    assert document.specs[CRAFT_PLAYER] == {"bath": "alum"}
    assert CONCEPT_PLAYER not in {c.label for c in document.content.components}
    player = next(c for c in document.content.components if c.label == CRAFT_PLAYER)
    assert (player.chapter, player.field, player.fields) == ("chem", "CHEMISTRY", ["PROCESS"])


async def test_a_family_and_a_category_get_their_own_documents(session: AsyncSession) -> None:
    family = await generated_document(session, "family", FAMILY_SLUG)
    assert family is not None
    assert (family.subject_kind, family.page_url.endswith(f"/crafts/{FAMILY_SLUG}")) == ("family", True)
    assert any("print with carved wooden" in text for text in texts(family))
    category = await generated_document(session, "category", CATEGORY_SLUG)
    assert category is not None
    assert (category.subject_kind, category.title) == ("category", "Page Docs Test Category")
    assert category.page_url.endswith(f"/categories/{CATEGORY_SLUG}")
    assert any("dye, print and weave" in text for text in texts(category))
    parts = await generated_parts(session, await subject_by_key(session, "category", CATEGORY_SLUG))
    assert parts is not None and [c.label for c in parts.components] == [CONCEPT_PLAYER]


async def test_a_subject_with_nothing_published_has_none_and_an_unknown_one_is_refused(
    session: AsyncSession,
) -> None:
    assert await generated_document(session, "craft", BARE_SLUG) is None
    with pytest.raises(InvalidInput):
        await generated_document(session, "family", CRAFT_SLUG)
    with pytest.raises(InvalidInput):
        await generated_document(session, "category", "No-Such-Category-Here")


async def test_the_stored_layout_orders_the_page_and_crops_its_picture(session: AsyncSession) -> None:
    before = await generated_document(session, "craft", CRAFT_SLUG)
    assert before is not None
    sentence = next(key for key, unit in before.content.units.items() if CRAFT_TEXT[:20] in str(unit.nodes))
    entries = [
        {"ref": sentence, "chapter": "glance", "order": 1, "role": "PULL_QUOTE"},
        {
            "ref": PICTURE,
            "chapter": "chem",
            "order": 1,
            "role": "PLATE",
            "crop": {"x": 0, "y": 0, "width": 0.5, "height": 0.5},
        },
    ]
    admin = await session.get(User, ADMIN)
    await write_layout(
        session,
        "craft",
        CRAFT_SLUG,
        LayoutWrite.model_validate({"baseVersion": 0, "entries": entries}),
        actor=admin,
    )
    after = await generated_document(session, "craft", CRAFT_SLUG)
    assert after is not None
    assert [(e.chapter, e.ref) for e in after.content.layout if e.ref in {sentence, PICTURE}] == [
        ("glance", sentence),
        ("chem", PICTURE),
    ]
    assert after.content.units[sentence].chapter == "glance"
    assert after.specs[PICTURE]["picture"]["focal"]["width"] == 0.5
    layout = after.content.data["page-layout"]
    assert layout["version"] == 1
    assert next(entry["role"] for entry in layout["entries"] if entry["ref"] == PICTURE) == "PLATE"
    assert all(e.within is None for e in after.content.layout if e.ref not in plate_units(after, PICTURE))
