from collections.abc import Sequence

from alembic import op

revision: str = "0011_first_password_proof"
down_revision: str | Sequence[str] | None = "0010_oidc_sign_in"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("AuthNoncePurpose", ("FIRST_PASSWORD",)),)

AUTH_NONCE_PURPOSES_BEFORE = ("GOOGLE_SIGN_IN", "GOOGLE_LINK", "OIDC_SIGN_IN")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    purposes = ", ".join(f"'{value}'" for value in AUTH_NONCE_PURPOSES_BEFORE)
    op.execute("DELETE FROM \"AuthNonce\" WHERE purpose::text = 'FIRST_PASSWORD'")
    op.execute('ALTER TYPE "AuthNoncePurpose" RENAME TO "AuthNoncePurpose_before_0011"')
    op.execute(f'CREATE TYPE "AuthNoncePurpose" AS ENUM ({purposes})')
    op.execute(
        'ALTER TABLE "AuthNonce" ALTER COLUMN purpose TYPE "AuthNoncePurpose" '
        'USING purpose::text::"AuthNoncePurpose"'
    )
    op.execute('DROP TYPE "AuthNoncePurpose_before_0011"')
