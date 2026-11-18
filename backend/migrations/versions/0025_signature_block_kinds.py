from collections.abc import Sequence

from alembic import op

revision: str = "0025_signature_block_kinds"
down_revision: str | Sequence[str] | None = "0024_piece_content_hash_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "KnowledgePiece"
CONSTRAINT = "KnowledgePiece_kind_check"
BLOCK_KINDS_BEFORE = (
    "prose",
    "process_ladder",
    "region_story",
    "map_layer",
    "reaction_player",
    "material_card",
    "molecule_3d",
    "images",
    "simulation",
    "what_if",
    "timeline_map",
    "zoom_story",
    "expert_view",
    "seasons",
    "supply_map",
    "compare",
    "in_practice",
    "quiz",
    "open_questions",
    "artisan_voice",
    "designs",
    "concept_graph",
    "measure",
    "market_gi",
    "climate_risk",
)
ADDED_KINDS = ("indigo_vat", "mordant_bath", "lost_wax", "firing")
BLOCK_KINDS = (*BLOCK_KINDS_BEFORE, *ADDED_KINDS)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _check_kinds(kinds: Sequence[str]) -> None:
    op.drop_constraint(op.f(CONSTRAINT), TABLE, type_="check")
    op.create_check_constraint(op.f(CONSTRAINT), TABLE, f'"kind" IN ({_listed(kinds)})')


def upgrade() -> None:
    _check_kinds(BLOCK_KINDS)


def downgrade() -> None:
    op.execute(f'DELETE FROM "{TABLE}" WHERE "kind" IN ({_listed(ADDED_KINDS)})')
    _check_kinds(BLOCK_KINDS_BEFORE)
