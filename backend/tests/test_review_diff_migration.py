from app.models import DrawnPicture, PageProposal
from app.models.page_proposals import DRAWN_SIDES

from .migration_scripts import migration


def test_the_review_diff_migration_follows_the_coded_figures() -> None:
    step = migration("0122_review_diff")
    assert (step.revision, step.down_revision) == ("0122_review_diff", "0122_design_feedback")


def test_it_creates_the_two_tables_and_widens_the_staged_kinds_by_page_proposals_alone() -> None:
    step = migration("0122_review_diff")
    tables = (PageProposal.__tablename__, DrawnPicture.__tablename__)
    assert tables == step.TABLES
    assert step.KINDS_BEFORE == migration("0119_picture_checks").KINDS
    assert step.KINDS == migration("0125_section_proposals").KINDS_BEFORE
    assert set(step.KINDS) - set(step.KINDS_BEFORE) == {"PAGES"}
    assert step.SIDES == DRAWN_SIDES
