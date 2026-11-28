import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.checks import default_context
from app.curation.dossier import Dossier
from app.curation.dossier_text import dossier_text
from app.curation.files import CURATION_DIR
from app.models import ArticleSection, Craft, User
from app.research.article_sections import SectionSentence
from app.services.curation_import import IMPORTED, import_dossier, import_path
from app.services.dossier_export import export_dossier
from app.services.monograph_generated_sections import ReviewedBy, SectionOwner, publish_reviewed_section

from ..curation.import_support import checked
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

SLUG = "Bagru-Hand-Block-Print"
NOW = datetime(2026, 11, 28, 15, 0, tzinfo=UTC)
WRITTEN = "Reviewed: "


@dataclass(frozen=True)
class Page:
    session: AsyncSession
    craft_id: uuid.UUID
    writer: User
    reviewer: User


@pytest.fixture
async def page() -> AsyncIterator[Page]:
    async for opened in rolled_back_session():
        outcome = await import_path(opened, CURATION_DIR / f"{SLUG}.json", default_context())
        assert outcome.status == IMPORTED, outcome.problems
        writer, reviewer = _person("RESEARCHER"), _person("PROFESSOR")
        opened.add_all([writer, reviewer])
        await opened.flush()
        craft_id = await opened.scalar(select(Craft.id).where(Craft.slug == SLUG))
        assert craft_id is not None
        yield Page(opened, craft_id, writer, reviewer)


def _person(role: str) -> User:
    token = uuid.uuid4()
    return User(id=token, name=f"{role.title()} Writer", email=f"{token.hex[:12]}@example.org", role=role)


async def _rows(page: Page) -> list[tuple[Any, ...]]:
    found = await page.session.execute(
        select(
            ArticleSection.id,
            ArticleSection.field,
            ArticleSection.version,
            ArticleSection.status,
            ArticleSection.writtenByKind,
        )
        .where(ArticleSection.craftId == page.craft_id)
        .order_by(ArticleSection.field, ArticleSection.version)
    )
    return [tuple(row) for row in found.all()]


async def _published(page: Page, field: str) -> ArticleSection:
    row = await page.session.scalar(
        select(ArticleSection)
        .where(
            ArticleSection.craftId == page.craft_id,
            ArticleSection.field == field,
            ArticleSection.status == "PUBLISHED",
        )
        .execution_options(populate_existing=True)
    )
    assert row is not None
    return row


async def _reviewed(page: Page) -> ArticleSection:
    machine = await page.session.scalar(
        select(ArticleSection)
        .where(ArticleSection.craftId == page.craft_id, ArticleSection.status == "PUBLISHED")
        .order_by(ArticleSection.field)
        .limit(1)
    )
    assert machine is not None and machine.writtenByKind == "SYSTEM"
    sentences = [
        SectionSentence.model_validate({**sentence, "text": WRITTEN + sentence["text"]})
        for sentence in machine.sentences
    ]
    reviewed = ReviewedBy(writer_id=page.writer.id, reviewer_id=page.reviewer.id, at=NOW)
    owner = SectionOwner.craft(page.craft_id)
    section_id = await publish_reviewed_section(page.session, owner, machine.field, sentences, reviewed)
    row = await page.session.get(ArticleSection, section_id)
    assert row is not None
    return row


async def _exported(page: Page) -> Dossier:
    return (await export_dossier(page.session, SLUG)).exported.dossier


async def _import(page: Page, dossier: Dossier) -> dict[str, int]:
    check = checked(SLUG).check
    assert check is not None
    outcome = await import_dossier(page.session, dossier, check, digest="2" * 64)
    assert outcome.status == IMPORTED, outcome.problems
    return outcome.changed


async def test_the_export_carries_a_reviewed_section_with_its_facts_version_and_reviewer_not_its_writer(
    page: Page,
) -> None:
    row = await _reviewed(page)
    found = await export_dossier(page.session, SLUG)
    (section,) = found.exported.dossier.sections
    assert (section.field, section.version, section.reviewed_by, section.reviewed_at) == (
        row.field,
        row.version,
        page.reviewer.id,
        NOW,
    )
    assert [
        sentence.model_dump(mode="json", by_alias=True) for sentence in section.sentences
    ] == row.sentences
    assert f"sections: added {row.field}" in found.changes
    text = dossier_text(found.exported.dossier)
    assert str(page.reviewer.id) in text and str(page.writer.id) not in text


async def test_an_exported_reviewed_section_is_imported_unchanged(page: Page) -> None:
    await _reviewed(page)
    exported = await _exported(page)
    before = await _rows(page)
    changed = await _import(page, exported)
    assert "sections" not in changed
    assert await _rows(page) == before


async def test_an_import_without_the_section_leaves_the_published_one_in_place(page: Page) -> None:
    row = await _reviewed(page)
    before = await _rows(page)
    outcome = await import_path(page.session, CURATION_DIR / f"{SLUG}.json", default_context())
    assert outcome.status == IMPORTED, outcome.problems
    assert await _rows(page) == before
    assert (await _published(page, row.field)).id == row.id


async def test_a_reviewed_section_the_database_lost_is_restored_from_the_export(page: Page) -> None:
    row = await _reviewed(page)
    field, version, sentences = row.field, row.version, list(row.sentences)
    exported = await _exported(page)
    await page.session.delete(row)
    await page.session.flush()
    changed = await _import(page, exported)
    assert changed.get("sections", 0) >= 1
    restored = await _published(page, field)
    assert (restored.writtenByKind, restored.version, restored.sentences) == ("USER", version, sentences)
    assert (restored.reviewedById, restored.reviewedAt, restored.writtenById) == (page.reviewer.id, NOW, None)


async def test_an_export_never_replaces_a_section_a_person_wrote_in_the_database(page: Page) -> None:
    row = await _reviewed(page)
    exported = await _exported(page)
    (section,) = exported.sections
    other = [SectionSentence(text="Another reviewed sentence.", claim_ids=section.claim_ids()[:1])]
    edited = exported.model_copy(update={"sections": [section.model_copy(update={"sentences": other})]})
    before = await _rows(page)
    await _import(page, edited)
    assert await _rows(page) == before
    assert (await _published(page, row.field)).sentences == row.sentences


async def test_a_reviewed_section_citing_facts_readers_cannot_see_is_not_restored(page: Page) -> None:
    row = await _reviewed(page)
    field = row.field
    exported = await _exported(page)
    (section,) = exported.sections
    unseen = [SectionSentence(text="A sentence of an unknown fact.", claim_ids=[uuid.uuid4()])]
    edited = exported.model_copy(update={"sections": [section.model_copy(update={"sentences": unseen})]})
    await page.session.delete(row)
    await page.session.flush()
    await _import(page, edited)
    assert (await _published(page, field)).writtenByKind == "SYSTEM"
