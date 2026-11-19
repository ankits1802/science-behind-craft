from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037_oauth"
down_revision: str | Sequence[str] | None = "0036_candidate_gates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAMP = sa.DateTime(timezone=True)
TABLES = ("OAuthClient", "OAuthGrant", "OAuthCode", "OAuthToken", "McpTermsAcceptance", "McpToolCall")
SCOPES = ("read", "ask", "contribute", "review")
TOKEN_KINDS = ("ACCESS", "REFRESH")
TOOL_OUTCOMES = ("OK", "TOOL_ERROR", "PROTOCOL_ERROR")
INDEXED = (
    ("OAuthClient", ("createdAt",)),
    ("OAuthGrant", ("userId", "revokedAt")),
    ("OAuthGrant", ("clientId",)),
    ("OAuthCode", ("clientId",)),
    ("OAuthCode", ("userId",)),
    ("OAuthCode", ("grantId",)),
    ("OAuthCode", ("expiresAt",)),
    ("OAuthToken", ("grantId",)),
    ("OAuthToken", ("expiresAt",)),
    ("McpToolCall", ("grantId", "calledAt")),
    ("McpToolCall", ("tokenId",)),
    ("McpToolCall", ("calledAt",)),
)

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
    _client_table()
    _grant_table()
    _code_table()
    _token_table()
    _terms_table()
    _tool_call_table()
    for table, columns in INDEXED:
        op.create_index(op.f(f"{table}_{'_'.join(columns)}_idx"), table, list(columns))
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)


def _client_table() -> None:
    op.create_table(
        "OAuthClient",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("redirectUris", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("clientUri", sa.Text(), nullable=True),
        sa.Column("softwareId", sa.String(length=120), nullable=True),
        sa.Column("softwareVersion", sa.String(length=120), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        _check("OAuthClient", "redirect_uris", 'cardinality("redirectUris") BETWEEN 1 AND 10'),
        _primary_key("OAuthClient"),
    )


def _grant_table() -> None:
    op.create_table(
        "OAuthGrant",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("clientId", sa.UUID(), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("userTokenVersion", sa.Integer(), nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("lastUsedAt", STAMP, nullable=True),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("revokedAt", STAMP, nullable=True),
        _check("OAuthGrant", "scopes", _within("scopes", SCOPES)),
        _fk("OAuthGrant", "clientId", "OAuthClient", "CASCADE"),
        _fk("OAuthGrant", "userId", "User", "CASCADE"),
        _primary_key("OAuthGrant"),
    )


def _code_table() -> None:
    op.create_table(
        "OAuthCode",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codeHash", sa.String(length=64), nullable=False),
        sa.Column("clientId", sa.UUID(), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("redirectUri", sa.Text(), nullable=False),
        sa.Column("codeChallenge", sa.String(length=43), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("usedAt", STAMP, nullable=True),
        sa.Column("grantId", sa.UUID(), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        _check("OAuthCode", "scopes", _within("scopes", SCOPES)),
        sa.UniqueConstraint("codeHash", name=op.f("OAuthCode_codeHash_key")),
        _fk("OAuthCode", "clientId", "OAuthClient", "CASCADE"),
        _fk("OAuthCode", "userId", "User", "CASCADE"),
        _fk("OAuthCode", "grantId", "OAuthGrant", "SET NULL"),
        _primary_key("OAuthCode"),
    )


def _token_table() -> None:
    op.create_table(
        "OAuthToken",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("grantId", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("tokenHash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("usedAt", STAMP, nullable=True),
        sa.Column("revokedAt", STAMP, nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        _check("OAuthToken", "kind", f'"kind" IN ({_listed(TOKEN_KINDS)})'),
        _check("OAuthToken", "scopes", _within("scopes", SCOPES)),
        sa.UniqueConstraint("tokenHash", name=op.f("OAuthToken_tokenHash_key")),
        _fk("OAuthToken", "grantId", "OAuthGrant", "CASCADE"),
        _primary_key("OAuthToken"),
    )


def _terms_table() -> None:
    op.create_table(
        "McpTermsAcceptance",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("termsVersion", sa.String(length=40), nullable=False),
        sa.Column("acceptedAt", STAMP, nullable=False),
        sa.UniqueConstraint(
            "userId", "termsVersion", name=op.f("McpTermsAcceptance_userId_termsVersion_key")
        ),
        _fk("McpTermsAcceptance", "userId", "User", "CASCADE"),
        _primary_key("McpTermsAcceptance"),
    )


def _tool_call_table() -> None:
    op.create_table(
        "McpToolCall",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("grantId", sa.UUID(), nullable=False),
        sa.Column("tokenId", sa.UUID(), nullable=True),
        sa.Column("tool", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("calledAt", STAMP, nullable=False),
        _check("McpToolCall", "outcome", f'"outcome" IN ({_listed(TOOL_OUTCOMES)})'),
        _fk("McpToolCall", "grantId", "OAuthGrant", "CASCADE"),
        _fk("McpToolCall", "tokenId", "OAuthToken", "SET NULL"),
        _primary_key("McpToolCall"),
    )


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _within(column: str, values: Sequence[str]) -> str:
    return f'"{column}" <@ ARRAY[{_listed(values)}]::text[]'


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{table}_{name}_check"))


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{table}_{column}_fkey"), ondelete=ondelete
    )


def _primary_key(table: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint("id", name=op.f(f"{table}_pkey"))
