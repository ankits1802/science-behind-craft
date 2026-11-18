from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_knowledge_fields"
down_revision: str | Sequence[str] | None = "0031_craft_page_chapters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAMP = sa.DateTime(timezone=True)
DISCIPLINES_BEFORE = (
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
)
DISCIPLINES = (*DISCIPLINES_BEFORE, "SOCIETY", "POLICY")
DOWNGRADED_FIELDS = (("SOCIETY", "OVERVIEW"), ("POLICY", "ECONOMICS"))
DISCIPLINE_CHECKS = (
    ("CuratedClaim", "discipline"),
    ("CuratedCategoryClaim", "discipline"),
    ("KnowledgePiece", "facet"),
    ("ArtisanContribution", "discipline"),
)
CONCEPT_TYPE_FIELDS = (
    ("TRADITION", "OVERVIEW"),
    ("HISTORICAL_CONTEXT", "HISTORY"),
    ("DESIGN_PRINCIPLE", "DESIGN"),
    ("PROCESS_STAGE", "PROCESS"),
    ("ARTISAN_ACTION", "PROCESS"),
    ("ARTISAN_DECISION", "PROCESS"),
    ("SENSORY_CUE", "PROCESS"),
    ("MATERIAL", "MATERIALS"),
    ("TOOL", "MATERIALS"),
    ("PROPERTY", "MATERIALS"),
    ("MECHANISM", "CHEMISTRY"),
    ("EXPLANATION", "CHEMISTRY"),
    ("CHANGE", "CHEMISTRY"),
    ("ENVIRONMENTAL_CONDITION", "GEOGRAPHY"),
)
SECTION_STATUSES = ("PROPOSED", "PUBLISHED", "SUPERSEDED", "RETRACTED")
PIECE_SUBJECT_KINDS = ("CRAFT", "CONCEPT", "PLACE", "COMPOUND")
SUBJECT_COLUMNS = (
    ("CRAFT", "craftId"),
    ("CONCEPT", "conceptId"),
    ("PLACE", "placeKey"),
    ("COMPOUND", "compoundId"),
)
LABEL_PATTERN = "^[a-z0-9]+(-[a-z0-9]+)*(/[a-z0-9]+(-[a-z0-9]+)*){2,}$"
PLACE_KEY_PATTERN = "^(lgd|basin):[A-Za-z0-9_-]+$"
DESCRIPTION_MAX_CHARS = 600
NEW_TABLES = ("ArticleSection", "KnowledgePieceSubject")

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "{table}" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""

FIELD_FROM_CURATED = """
UPDATE "Claim" AS c SET "field" = cc."discipline"
FROM "{table}" AS cc
WHERE cc."claimId" = c."id" AND c."field" IS NULL
"""

FIELD_FROM_TESTIMONY = """
UPDATE "Claim" AS c SET "field" = ac."discipline"
FROM "ArtisanContribution" AS ac
WHERE ac."claimId" = c."id" AND c."field" IS NULL
"""

FIELD_FROM_FIRST_PIECE = """
WITH first_piece AS (
    SELECT DISTINCT ON (cited."claimId") cited."claimId", kp."facet"
    FROM "KnowledgePiece" AS kp
    CROSS JOIN LATERAL unnest(kp."claimIds") AS cited("claimId")
    ORDER BY cited."claimId", kp."createdAt", kp."id"
)
UPDATE "Claim" AS c SET "field" = first_piece."facet"
FROM first_piece
WHERE first_piece."claimId" = c."id" AND c."field" IS NULL
"""

FIELD_FROM_CONCEPT_TYPE = """
UPDATE "Claim" AS c SET "field" = CASE co."type"::text {cases} END
FROM "Concept" AS co
WHERE c."subjectType" = 'CONCEPT' AND co."id" = c."subjectId" AND c."field" IS NULL
  AND co."type"::text IN ({types})
"""

FIELDS_FROM_PIECES = """
WITH piece_fields AS (
    SELECT cited."claimId", array_agg(DISTINCT kp."facet"::text ORDER BY kp."facet"::text) AS facets
    FROM "KnowledgePiece" AS kp
    CROSS JOIN LATERAL unnest(kp."claimIds") AS cited("claimId")
    GROUP BY cited."claimId"
)
UPDATE "Claim" AS c SET "fields" = array_remove(piece_fields."facets", c."field"::text)
FROM piece_fields
WHERE piece_fields."claimId" = c."id" AND c."field" IS NOT NULL
  AND cardinality(array_remove(piece_fields."facets", c."field"::text)) > 0
"""


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _within(column: str, values: Sequence[str]) -> str:
    return f'"{column}" <@ ARRAY[{_listed(values)}]::text[]'


def backfill_statements() -> tuple[str, ...]:
    cases = " ".join(f"WHEN '{kind}' THEN '{field}'" for kind, field in CONCEPT_TYPE_FIELDS)
    types = _listed([kind for kind, _ in CONCEPT_TYPE_FIELDS])
    return (
        FIELD_FROM_CURATED.replace("{table}", "CuratedClaim"),
        FIELD_FROM_CURATED.replace("{table}", "CuratedCategoryClaim"),
        FIELD_FROM_TESTIMONY,
        FIELD_FROM_FIRST_PIECE,
        FIELD_FROM_CONCEPT_TYPE.replace("{cases}", cases).replace("{types}", types),
        FIELDS_FROM_PIECES,
    )


def upgrade() -> None:
    _set_discipline_checks(DISCIPLINES)
    _claim_fields()
    for statement in backfill_statements():
        op.execute(statement)
    _piece_registry()
    _piece_subjects()
    _article_sections()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    op.drop_index("KnowledgePiece_fields_gin_idx", table_name="KnowledgePiece")
    op.drop_index("KnowledgePiece_label_key", table_name="KnowledgePiece")
    for name in ("description", "label", "facet_once", "fields"):
        op.drop_constraint(op.f(f"KnowledgePiece_{name}_check"), "KnowledgePiece", type_="check")
    for column in ("fields", "description", "title", "label"):
        op.drop_column("KnowledgePiece", column)
    op.drop_index("Claim_fields_gin_idx", table_name="Claim")
    op.drop_index(op.f("Claim_field_idx"), table_name="Claim")
    for name in ("field_once", "fields_need_field", "fields", "field"):
        op.drop_constraint(op.f(f"Claim_{name}_check"), "Claim", type_="check")
    op.drop_column("Claim", "fields")
    op.drop_column("Claim", "field")
    for table, column in DISCIPLINE_CHECKS:
        for new, old in DOWNGRADED_FIELDS:
            op.execute(f'UPDATE "{table}" SET "{column}" = \'{old}\' WHERE "{column}" = \'{new}\'')
    _set_discipline_checks(DISCIPLINES_BEFORE)


def _set_discipline_checks(values: Sequence[str]) -> None:
    for table, column in DISCIPLINE_CHECKS:
        name = op.f(f"{table}_{column}_check")
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, f'"{column}" IN ({_listed(values)})')


def _claim_fields() -> None:
    op.add_column("Claim", sa.Column("field", sa.String(length=16), nullable=True))
    op.add_column(
        "Claim",
        sa.Column(
            "fields", postgresql.ARRAY(sa.Text()), server_default=sa.text("ARRAY[]::text[]"), nullable=False
        ),
    )
    op.create_check_constraint(
        op.f("Claim_field_check"), "Claim", f'"field" IS NULL OR "field" IN ({_listed(DISCIPLINES)})'
    )
    op.create_check_constraint(op.f("Claim_fields_check"), "Claim", _within("fields", DISCIPLINES))
    op.create_check_constraint(
        op.f("Claim_fields_need_field_check"), "Claim", '"field" IS NOT NULL OR cardinality("fields") = 0'
    )
    op.create_check_constraint(op.f("Claim_field_once_check"), "Claim", 'NOT ("field" = ANY ("fields"))')
    op.create_index(op.f("Claim_field_idx"), "Claim", ["field"])
    op.create_index("Claim_fields_gin_idx", "Claim", ["fields"], postgresql_using="gin")


def _piece_registry() -> None:
    op.add_column("KnowledgePiece", sa.Column("label", sa.String(length=200), nullable=True))
    op.add_column("KnowledgePiece", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("KnowledgePiece", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "KnowledgePiece",
        sa.Column(
            "fields", postgresql.ARRAY(sa.Text()), server_default=sa.text("ARRAY[]::text[]"), nullable=False
        ),
    )
    op.create_check_constraint(
        op.f("KnowledgePiece_fields_check"), "KnowledgePiece", _within("fields", DISCIPLINES)
    )
    op.create_check_constraint(
        op.f("KnowledgePiece_facet_once_check"), "KnowledgePiece", 'NOT ("facet" = ANY ("fields"))'
    )
    op.create_check_constraint(
        op.f("KnowledgePiece_label_check"),
        "KnowledgePiece",
        f'"label" IS NULL OR ("label" ~ \'{LABEL_PATTERN}\' AND "title" IS NOT NULL AND "description" IS NOT NULL)',
    )
    op.create_check_constraint(
        op.f("KnowledgePiece_description_check"),
        "KnowledgePiece",
        f'"description" IS NULL OR char_length("description") <= {DESCRIPTION_MAX_CHARS}',
    )
    op.create_index(
        "KnowledgePiece_label_key",
        "KnowledgePiece",
        ["label"],
        unique=True,
        postgresql_where=sa.text('"label" IS NOT NULL'),
    )
    op.create_index("KnowledgePiece_fields_gin_idx", "KnowledgePiece", ["fields"], postgresql_using="gin")


def _one_subject() -> str:
    return " AND ".join(
        f'("kind" = \'{kind}\') = ("{column}" IS NOT NULL)' for kind, column in SUBJECT_COLUMNS
    )


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{table}_{column}_fkey"), ondelete=ondelete
    )


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{table}_{name}_check"))


def _piece_subjects() -> None:
    table = "KnowledgePieceSubject"
    op.create_table(
        table,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pieceId", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("conceptId", sa.UUID(), nullable=True),
        sa.Column("compoundId", sa.UUID(), nullable=True),
        sa.Column("placeKey", sa.String(length=64), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        _check(table, "kind", f'"kind" IN ({_listed(PIECE_SUBJECT_KINDS)})'),
        _check(table, "one_subject", _one_subject()),
        _check(table, "placeKey", f'"placeKey" IS NULL OR "placeKey" ~ \'{PLACE_KEY_PATTERN}\''),
        _fk(table, "pieceId", "KnowledgePiece", "CASCADE"),
        _fk(table, "craftId", "Craft", "CASCADE"),
        _fk(table, "conceptId", "Concept", "CASCADE"),
        _fk(table, "compoundId", "Compound", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{table}_pkey")),
    )
    for _, column in SUBJECT_COLUMNS:
        op.create_index(
            f"{table}_pieceId_{column}_key",
            table,
            ["pieceId", column],
            unique=True,
            postgresql_where=sa.text(f'"{column}" IS NOT NULL'),
        )
        op.create_index(op.f(f"{table}_{column}_idx"), table, [column])


def _section_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("categoryId", sa.UUID(), nullable=True),
        sa.Column("field", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sentences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PROPOSED", nullable=False),
        sa.Column(
            "writtenByKind",
            postgresql.ENUM(name="ActorKind", create_type=False),
            server_default="SYSTEM",
            nullable=False,
        ),
        sa.Column("writtenById", sa.UUID(), nullable=True),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
    )


def _section_rules(table: str) -> tuple[sa.Constraint, ...]:
    return (
        _check(table, "field", f'"field" IN ({_listed(DISCIPLINES)})'),
        _check(table, "status", f'"status" IN ({_listed(SECTION_STATUSES)})'),
        _check(table, "version", '"version" >= 1'),
        _check(table, "one_subject", '("craftId" IS NULL) <> ("categoryId" IS NULL)'),
        _check(
            table,
            "sentences",
            'jsonb_typeof("sentences") = \'array\' AND jsonb_array_length("sentences") > 0',
        ),
        _check(table, "reviewed_by", '"reviewedById" IS NULL OR "reviewedAt" IS NOT NULL'),
        _fk(table, "craftId", "Craft", "CASCADE"),
        _fk(table, "categoryId", "CraftCategory", "CASCADE"),
        _fk(table, "writtenById", "User", "SET NULL"),
        _fk(table, "reviewedById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{table}_pkey")),
    )


def _article_sections() -> None:
    table = "ArticleSection"
    op.create_table(table, *_section_columns(), *_section_rules(table))
    for column in ("craftId", "categoryId"):
        op.create_index(
            f"{table}_{column}_field_version_key",
            table,
            [column, "field", "version"],
            unique=True,
            postgresql_where=sa.text(f'"{column}" IS NOT NULL'),
        )
        op.create_index(
            f"{table}_{column}_field_published_key",
            table,
            [column, "field"],
            unique=True,
            postgresql_where=sa.text(f'"{column}" IS NOT NULL AND "status" = \'PUBLISHED\''),
        )
    op.create_index(op.f(f"{table}_writtenById_idx"), table, ["writtenById"])
    op.create_index(op.f(f"{table}_reviewedById_idx"), table, ["reviewedById"])
