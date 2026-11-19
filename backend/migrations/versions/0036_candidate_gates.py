from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036_candidate_gates"
down_revision: str | Sequence[str] | None = "0035_answer_components"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "CandidateCheck"
STAMP = sa.DateTime(timezone=True)
CANDIDATE_GATES = ("QUOTES", "SOURCE", "DUPLICATE", "NOVELTY")

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "CandidateCheck" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "CandidateCheck",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("gate", sa.String(length=16), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "relatedClaimIds",
            postgresql.ARRAY(sa.UUID()),
            server_default=sa.text("ARRAY[]::uuid[]"),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("checkedAt", STAMP, nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        sa.CheckConstraint(f'"gate" IN ({_listed(CANDIDATE_GATES)})', name=op.f(f"{TABLE}_gate_check")),
        sa.CheckConstraint(
            'jsonb_typeof("reasons") = \'array\' AND jsonb_array_length("reasons") > 0',
            name=op.f(f"{TABLE}_reasons_check"),
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f(f"{TABLE}_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("claimId", "gate", name=op.f(f"{TABLE}_claimId_gate_key")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
