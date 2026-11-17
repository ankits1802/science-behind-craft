from pathlib import Path

from alembic.script import ScriptDirectory

VERSION_NUM_LENGTH = 32
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def test_every_revision_id_fits_the_alembic_version_column():
    scripts = ScriptDirectory(str(MIGRATIONS))
    too_long = [rev.revision for rev in scripts.walk_revisions() if len(rev.revision) > VERSION_NUM_LENGTH]
    assert too_long == []


def test_the_migrations_have_one_head():
    assert len(ScriptDirectory(str(MIGRATIONS)).get_heads()) == 1
