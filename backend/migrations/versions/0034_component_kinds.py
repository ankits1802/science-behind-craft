from collections.abc import Sequence

from alembic import op

revision: str = "0034_component_kinds"
down_revision: str | Sequence[str] | None = "0033_image_contributions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "KnowledgePiece"
CONSTRAINT = "KnowledgePiece_kind_check"
BLOCK_KINDS = (
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
    "indigo_vat",
    "mordant_bath",
    "lost_wax",
    "firing",
)
COMPONENT_KINDS = (
    "ai_illustration",
    "ai_video",
    "ask_next",
    "audio_player",
    "chart",
    "choice_toggle",
    "citation_tool",
    "comic",
    "concept_atlas",
    "credits",
    "diagram",
    "dip_player",
    "equation_card",
    "experiment_lab",
    "explainer",
    "fact_table",
    "film",
    "generator",
    "label_card",
    "language_switch",
    "map_sequence",
    "material_cards",
    "model_explainer",
    "picture_plate",
    "process_replay",
    "reading_level",
    "related_crafts",
    "source_disagreements",
    "source_list",
    "specimen_plate",
    "stage_player",
    "stat_tiles",
    "structure_diagram",
    "swatch_cards",
    "swatch_pair",
    "timeline",
    "voice",
)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _check_kinds(kinds: Sequence[str]) -> None:
    op.drop_constraint(op.f(CONSTRAINT), TABLE, type_="check")
    op.create_check_constraint(op.f(CONSTRAINT), TABLE, f'"kind" IN ({_listed(kinds)})')


def upgrade() -> None:
    _check_kinds((*BLOCK_KINDS, *COMPONENT_KINDS))


def downgrade() -> None:
    op.execute(f'DELETE FROM "{TABLE}" WHERE "kind" IN ({_listed(COMPONENT_KINDS)})')
    _check_kinds(BLOCK_KINDS)
