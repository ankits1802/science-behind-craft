from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_science_storage"
down_revision: str | Sequence[str] | None = "0003_claim_source_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("ReactionCitation", "ProcessCondition", "ConditionReading")

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "ReactionCitation", "ProcessCondition", "ConditionReading" FROM %I',
                grantee);
        END IF;
    END LOOP;
END
$do$
"""

DROP_REPEATED_MATERIAL_NAMES = (
    'DELETE FROM "Material" later USING "Material" earlier '
    'WHERE later."nameNorm" = earlier."nameNorm" AND later.id > earlier.id'
)


def upgrade() -> None:
    _change_reaction()
    _change_material()
    _create_reaction_citation()
    _create_process_condition()
    _create_condition_reading()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table("ConditionReading")
    op.drop_table("ProcessCondition")
    op.drop_table("ReactionCitation")
    op.drop_constraint(op.f("Material_nameNorm_conceptId_key"), "Material", type_="unique")
    op.execute(DROP_REPEATED_MATERIAL_NAMES)
    op.create_unique_constraint(op.f("Material_nameNorm_key"), "Material", ["nameNorm"])
    op.drop_constraint(op.f("Reaction_deltaHClaimId_fkey"), "Reaction", type_="foreignkey")
    op.drop_column("Reaction", "deltaHClaimId")
    op.drop_column("Reaction", "label")
    op.drop_column("Reaction", "ordinal")
    op.alter_column("Reaction", "species", server_default=sa.text("'{}'::jsonb"))
    op.add_column(
        "Reaction",
        sa.Column("conditions", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )


def _change_reaction() -> None:
    op.add_column("Reaction", sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("Reaction", sa.Column("label", sa.String(length=200), nullable=False))
    op.add_column("Reaction", sa.Column("deltaHClaimId", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("Reaction_deltaHClaimId_fkey"),
        "Reaction",
        "Claim",
        ["deltaHClaimId"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("Reaction", "species", server_default=sa.text("'[]'::jsonb"))
    op.drop_column("Reaction", "conditions")


def _change_material() -> None:
    op.drop_constraint(op.f("Material_nameNorm_key"), "Material", type_="unique")
    op.create_unique_constraint(
        op.f("Material_nameNorm_conceptId_key"),
        "Material",
        ["nameNorm", "conceptId"],
        postgresql_nulls_not_distinct=True,
    )


def _create_reaction_citation() -> None:
    op.create_table(
        "ReactionCitation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("reactionId", sa.UUID(), nullable=False),
        sa.Column("claimSourceId", sa.UUID(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["reactionId"], ["Reaction.id"], name=op.f("ReactionCitation_reactionId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["claimSourceId"],
            ["ClaimSource.id"],
            name=op.f("ReactionCitation_claimSourceId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ReactionCitation_pkey")),
        sa.UniqueConstraint(
            "reactionId", "claimSourceId", name=op.f("ReactionCitation_reactionId_claimSourceId_key")
        ),
    )
    op.create_index(
        op.f("ReactionCitation_claimSourceId_idx"), "ReactionCitation", ["claimSourceId"], unique=False
    )


def _create_process_condition() -> None:
    op.create_table(
        "ProcessCondition",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stageId", sa.UUID(), nullable=True),
        sa.Column("reactionId", sa.UUID(), nullable=True),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.String(length=20), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            'num_nonnulls("stageId", "reactionId") = 1', name=op.f("ProcessCondition_one_owner_check")
        ),
        sa.ForeignKeyConstraint(
            ["stageId"], ["ProcessStage.id"], name=op.f("ProcessCondition_stageId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reactionId"], ["Reaction.id"], name=op.f("ProcessCondition_reactionId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ProcessCondition_pkey")),
        sa.UniqueConstraint(
            "stageId",
            "reactionId",
            "key",
            name=op.f("ProcessCondition_stageId_reactionId_key_key"),
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(op.f("ProcessCondition_reactionId_idx"), "ProcessCondition", ["reactionId"], unique=False)


def _create_condition_reading() -> None:
    op.create_table(
        "ConditionReading",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conditionId", sa.UUID(), nullable=False),
        sa.Column("claimSourceId", sa.UUID(), nullable=False),
        sa.Column("stated", sa.String(length=200), nullable=False),
        sa.Column("statedMin", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("statedMax", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("statedUnit", sa.String(length=40), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            'num_nonnulls("statedMin", "statedMax") >= 1', name=op.f("ConditionReading_bounded_check")
        ),
        sa.ForeignKeyConstraint(
            ["conditionId"],
            ["ProcessCondition.id"],
            name=op.f("ConditionReading_conditionId_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claimSourceId"],
            ["ClaimSource.id"],
            name=op.f("ConditionReading_claimSourceId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ConditionReading_pkey")),
        sa.UniqueConstraint(
            "conditionId",
            "claimSourceId",
            "stated",
            name=op.f("ConditionReading_conditionId_claimSourceId_stated_key"),
        ),
    )
    op.create_index(
        op.f("ConditionReading_claimSourceId_idx"), "ConditionReading", ["claimSourceId"], unique=False
    )
