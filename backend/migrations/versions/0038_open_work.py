from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038_open_work"
down_revision: str | Sequence[str] | None = "0037_oauth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESERVATIONS = "TaskReservation"
PROPOSALS = "ComponentProposal"
STAMP = sa.DateTime(timezone=True)
RESERVATION_ENDINGS = ("RELEASED", "EXPIRED", "COMPLETED")
PROPOSAL_STATUSES = ("PENDING", "APPROVED", "REJECTED", "WITHDRAWN")
PROPOSAL_EXTENSIONS = ("SUBJECT_LINK", "VARIANT")
DISCIPLINES = (
    "OVERVIEW",
    "PROCESS",
    "CHEMISTRY",
    "PHYSICS",
    "MATERIALS",
    "GEOGRAPHY",
    "GEOLOGY",
    "CLIMATE",
    "ECOLOGY",
    "BOTANY",
    "HISTORY",
    "ECONOMICS",
    "DESIGN",
    "HEALTH",
    "SOCIETY",
    "POLICY",
)
PIECE_KINDS = (
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
DESCRIPTION_MAX_CHARS = 600
RESERVATION_INDEXES = (("userId", "endedAt"),)
PROPOSAL_INDEXES = (("status", "createdAt"), ("proposerId",), ("craftId",), ("reviewedById",), ("taskKey",))

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON %I FROM %I', '{table}', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    _create_reservations()
    _create_proposals()
    _create_live_keys()
    _index_and_lock(RESERVATIONS, RESERVATION_INDEXES)
    _index_and_lock(PROPOSALS, PROPOSAL_INDEXES)


def downgrade() -> None:
    op.drop_table(PROPOSALS)
    op.drop_table(RESERVATIONS)


def _create_reservations() -> None:
    op.create_table(
        "TaskReservation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("taskKey", sa.String(length=240), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("reservedAt", STAMP, nullable=False),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("endedAt", STAMP, nullable=True),
        sa.Column("ending", sa.String(length=16), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_reservation_rules(),
    )


def _create_proposals() -> None:
    op.create_table(
        "ComponentProposal",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("proposerId", sa.UUID(), nullable=True),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("field", sa.String(length=16), nullable=False),
        sa.Column(
            "fields", postgresql.ARRAY(sa.Text()), server_default=sa.text("ARRAY[]::text[]"), nullable=False
        ),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("subjects", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "consideredLabels",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column("extendsLabel", sa.String(length=200), nullable=True),
        sa.Column("extension", sa.String(length=16), nullable=True),
        sa.Column("taskKey", sa.String(length=240), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("reviewNote", sa.String(length=500), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_proposal_rules(),
    )


def _create_live_keys() -> None:
    op.create_index(
        "TaskReservation_taskKey_live_key",
        RESERVATIONS,
        ["taskKey"],
        unique=True,
        postgresql_where=sa.text('"endedAt" IS NULL'),
    )
    op.create_index(
        "ComponentProposal_label_live_key",
        PROPOSALS,
        ["label"],
        unique=True,
        postgresql_where=sa.text(
            f'"status" IN ({_listed(("PENDING", "APPROVED"))}) AND "extension" IS DISTINCT FROM \'SUBJECT_LINK\''
        ),
    )


def _index_and_lock(table: str, indexes: Sequence[tuple[str, ...]]) -> None:
    for columns in indexes:
        op.create_index(op.f(f"{table}_{'_'.join(columns)}_idx"), table, list(columns))
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{table}_{name}_check"))


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{table}_{column}_fkey"), ondelete=ondelete
    )


def _reservation_rules() -> tuple[sa.Constraint, ...]:
    return (
        _check(RESERVATIONS, "expires", '"expiresAt" > "reservedAt"'),
        _check(RESERVATIONS, "ending", f'"ending" IS NULL OR "ending" IN ({_listed(RESERVATION_ENDINGS)})'),
        _check(RESERVATIONS, "ended", '("endedAt" IS NULL) = ("ending" IS NULL)'),
        _fk(RESERVATIONS, "userId", "User", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{RESERVATIONS}_pkey")),
    )


def _proposal_rules() -> tuple[sa.Constraint, ...]:
    return (
        _check(PROPOSALS, "kind", f'"kind" IN ({_listed(PIECE_KINDS)})'),
        _check(PROPOSALS, "field", f'"field" IN ({_listed(DISCIPLINES)})'),
        _check(PROPOSALS, "fields", f'"fields" <@ ARRAY[{_listed(DISCIPLINES)}]::text[]'),
        _check(PROPOSALS, "field_once", 'NOT ("field" = ANY ("fields"))'),
        _check(PROPOSALS, "status", f'"status" IN ({_listed(PROPOSAL_STATUSES)})'),
        _check(PROPOSALS, "description", f'char_length("description") <= {DESCRIPTION_MAX_CHARS}'),
        _check(
            PROPOSALS,
            "subjects",
            'jsonb_typeof("subjects") = \'array\' AND jsonb_array_length("subjects") > 0',
        ),
        _check(
            PROPOSALS,
            "extension",
            '("extendsLabel" IS NULL) = ("extension" IS NULL) AND ("extension" IS NULL OR "extension" IN '
            f"({_listed(PROPOSAL_EXTENSIONS)}))",
        ),
        _check(
            PROPOSALS, "reviewed", "NOT \"status\" IN ('APPROVED', 'REJECTED') OR \"reviewedAt\" IS NOT NULL"
        ),
        _fk(PROPOSALS, "proposerId", "User", "SET NULL"),
        _fk(PROPOSALS, "craftId", "Craft", "CASCADE"),
        _fk(PROPOSALS, "reviewedById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{PROPOSALS}_pkey")),
    )
