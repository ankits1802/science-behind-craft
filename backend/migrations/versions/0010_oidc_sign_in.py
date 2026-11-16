from collections.abc import Sequence

from alembic import op

revision: str = "0010_oidc_sign_in"
down_revision: str | Sequence[str] | None = "0009_admin_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AuthProvider", ("MICROSOFT", "YAHOO")),
    ("AuthNoncePurpose", ("OIDC_SIGN_IN",)),
)

AUTH_PROVIDERS_BEFORE = ("LOCAL", "GOOGLE")
AUTH_NONCE_PURPOSES_BEFORE = ("GOOGLE_SIGN_IN", "GOOGLE_LINK")
PROVIDER_AFTER_DOWNGRADE = "LOCAL"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    purposes = ", ".join(f"'{value}'" for value in AUTH_NONCE_PURPOSES_BEFORE)
    providers = ", ".join(f"'{value}'" for value in AUTH_PROVIDERS_BEFORE)
    op.execute("DELETE FROM \"AuthNonce\" WHERE purpose::text = 'OIDC_SIGN_IN'")
    op.execute('ALTER TYPE "AuthNoncePurpose" RENAME TO "AuthNoncePurpose_before_0010"')
    op.execute(f'CREATE TYPE "AuthNoncePurpose" AS ENUM ({purposes})')
    op.execute(
        'ALTER TABLE "AuthNonce" ALTER COLUMN purpose TYPE "AuthNoncePurpose" '
        'USING purpose::text::"AuthNoncePurpose"'
    )
    op.execute('DROP TYPE "AuthNoncePurpose_before_0010"')
    op.execute('ALTER TYPE "AuthProvider" RENAME TO "AuthProvider_before_0010"')
    op.execute(f'CREATE TYPE "AuthProvider" AS ENUM ({providers})')
    op.execute('ALTER TABLE "User" ALTER COLUMN "authProvider" DROP DEFAULT')
    op.execute(
        'ALTER TABLE "User" ALTER COLUMN "authProvider" TYPE "AuthProvider" USING '
        "(CASE WHEN \"authProvider\"::text IN ('MICROSOFT', 'YAHOO') "
        f'THEN \'{PROVIDER_AFTER_DOWNGRADE}\' ELSE "authProvider"::text END)::"AuthProvider"'
    )
    op.execute(f'ALTER TABLE "User" ALTER COLUMN "authProvider" SET DEFAULT \'{PROVIDER_AFTER_DOWNGRADE}\'')
    op.execute('DROP TYPE "AuthProvider_before_0010"')
