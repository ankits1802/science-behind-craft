from app.models import ComponentProposal, KnowledgePiece
from app.models.component_kinds import PIECE_KINDS

from .migration_scripts import migration


def test_the_coded_figures_migration_follows_the_rest_after_removal() -> None:
    step = migration("0121_coded_figures")
    assert (step.revision, step.down_revision) == ("0121_coded_figures", "0120_rest_after_removal")


def test_it_widens_both_kind_checks_by_the_coded_figure_alone() -> None:
    step = migration("0121_coded_figures")
    before = migration("0111_answer_figures")
    assert (*before.BLOCK_KINDS, *before.COMPONENT_KINDS) == step.PIECE_KINDS_BEFORE
    assert set(step.PIECE_KINDS) - set(step.PIECE_KINDS_BEFORE) == {"coded_figure"}
    assert sorted(step.PIECE_KINDS) == sorted(PIECE_KINDS)
    assert (KnowledgePiece.__tablename__, ComponentProposal.__tablename__) == step.KIND_CHECKS
