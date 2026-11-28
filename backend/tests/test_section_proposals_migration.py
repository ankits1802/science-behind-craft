from app.models import SectionProposal
from app.models.admin_work import STAGED_KIND_VALUES
from app.models.enums import DISCIPLINES
from app.models.section_proposals import SECTION_PROPOSAL_ORIGINS, SECTION_PROPOSAL_STATUSES

from .migration_scripts import migration

COLUMNS = {
    "id",
    "proposerId",
    "craftId",
    "categoryId",
    "field",
    "sentences",
    "checks",
    "taskKey",
    "note",
    "origin",
    "status",
    "reviewedById",
    "reviewedAt",
    "reviewNote",
    "sectionId",
    "createdAt",
    "updatedAt",
}


def test_the_section_proposals_migration_follows_the_leftovers() -> None:
    step = migration("0125_section_proposals")
    assert (step.revision, step.down_revision) == ("0125_section_proposals", "0124_leftovers")


def test_it_creates_the_table_the_model_maps_and_widens_the_staged_kinds_by_sections_alone() -> None:
    step = migration("0125_section_proposals")
    assert step.TABLE == "SectionProposal" == SectionProposal.__tablename__
    assert {column.name for column in SectionProposal.__table__.columns} == COLUMNS
    assert (step.FIELDS, step.STATUSES, step.ORIGINS) == (
        DISCIPLINES,
        SECTION_PROPOSAL_STATUSES,
        SECTION_PROPOSAL_ORIGINS,
    )
    assert step.KINDS == STAGED_KIND_VALUES
    assert set(step.KINDS) - set(step.KINDS_BEFORE) == {"SECTIONS"}
    assert step.KINDS_BEFORE == migration("0122_review_diff").KINDS
