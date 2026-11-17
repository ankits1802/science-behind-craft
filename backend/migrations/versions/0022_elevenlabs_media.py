from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_elevenlabs_media"
down_revision: str | Sequence[str] | None = "0021_climate_trend_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AiProvider", ("ELEVENLABS",)),
    ("AiTask", ("MUSIC", "SOUND_EFFECT")),
)

AI_PROVIDERS_BEFORE = ("OPENAI", "GEMINI", "ANTHROPIC", "DEEPSEEK")
AI_TASKS_BEFORE = (
    "PROOFREAD",
    "EXPAND",
    "SUMMARISE",
    "TRANSLATE",
    "TRANSCRIBE",
    "CAPTION",
    "PLAN",
    "COMPOSE",
    "WEB_READ",
    "EXTRACT",
    "EMBED",
    "IMAGE",
    "VIDEO",
    "VOICE_TURN",
    "EVAL_JUDGE",
)
ENUM_COLUMNS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("AiProvider", (("Provider", "name"), ("UsageEvent", "provider"))),
    ("AiTask", (("RoutePolicy", "task"), ("UsageEvent", "task"))),
)

ELEVENLABS = {
    "name": "ELEVENLABS",
    "preset": "elevenlabs",
    "kind": "elevenlabs",
    "baseUrl": "https://api.elevenlabs.io",
    "apiKeySecretKey": "ELEVENLABS_API_KEY",
    "dataClass": "ANY",
    "maxConcurrency": 3,
}
SCORE_ROUTES: tuple[dict[str, str | int], ...] = (
    {"task": "MUSIC", "ordinal": 1, "model": "music_v2_5"},
    {"task": "SOUND_EFFECT", "ordinal": 1, "model": "eleven_text_to_sound_v3"},
)

INSERT_PROVIDER = (
    'INSERT INTO "Provider" (name, preset, kind, "baseUrl", "apiKeySecretKey", "dataClass", "maxConcurrency") '
    'VALUES (CAST(:name AS "AiProvider"), :preset, :kind, :baseUrl, :apiKeySecretKey, '
    'CAST(:dataClass AS "ProviderDataClass"), :maxConcurrency) ON CONFLICT (name) DO NOTHING'
)
INSERT_ROUTE = (
    'INSERT INTO "RoutePolicy" (task, ordinal, "providerId", model) '
    'SELECT CAST(:task AS "AiTask"), :ordinal, p.id, :model FROM "Provider" p '
    "WHERE p.name = CAST('ELEVENLABS' AS \"AiProvider\") "
    "ON CONFLICT (task, ordinal) DO NOTHING"
)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    op.execute(sa.text(INSERT_PROVIDER).bindparams(**ELEVENLABS))
    for route in SCORE_ROUTES:
        op.execute(sa.text(INSERT_ROUTE).bindparams(**route))


def downgrade() -> None:
    tasks = _listed([value for name, values in ENUM_ADDITIONS if name == "AiTask" for value in values])
    op.execute(
        f'DELETE FROM "RoutePolicy" WHERE task::text IN ({tasks}) OR "providerId" IN '
        "(SELECT id FROM \"Provider\" WHERE name::text = 'ELEVENLABS')"
    )
    op.execute(f"DELETE FROM \"UsageEvent\" WHERE task::text IN ({tasks}) OR provider::text = 'ELEVENLABS'")
    op.execute("DELETE FROM \"Provider\" WHERE name::text = 'ELEVENLABS'")
    before = {"AiProvider": AI_PROVIDERS_BEFORE, "AiTask": AI_TASKS_BEFORE}
    for enum_name, columns in ENUM_COLUMNS:
        op.execute(f'ALTER TYPE "{enum_name}" RENAME TO "{enum_name}_before_0022"')
        op.execute(f'CREATE TYPE "{enum_name}" AS ENUM ({_listed(before[enum_name])})')
        for table, column in columns:
            op.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE "{enum_name}" '
                f'USING "{column}"::text::"{enum_name}"'
            )
        op.execute(f'DROP TYPE "{enum_name}_before_0022"')
