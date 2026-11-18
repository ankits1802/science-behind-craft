from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.curation.files import CURATION_DIR, category_paths, dossier_paths
from app.curation.vocabulary import DOSSIER_SCHEMA_VERSION

from .output import relative_label, utf8_console, write_text_atomically

__all__ = ["Migrated", "MigrationFailed", "main", "migrate_files", "migrated_text"]

SCHEMA_KEY = "schemaVersion"
PREVIOUS_VERSION = DOSSIER_SCHEMA_VERSION - 1
VERSION_FIELD = re.compile(rf'("{SCHEMA_KEY}"\s*:\s*){PREVIOUS_VERSION}(?=\s*[,}}])')


class MigrationFailed(Exception):
    pass


@dataclass(frozen=True)
class Migrated:
    rewritten: tuple[Path, ...]
    current: tuple[Path, ...]


def migrated_text(text: str) -> str | None:
    plain = json.loads(text)
    if not isinstance(plain, dict) or SCHEMA_KEY not in plain:
        raise MigrationFailed(f"is not a dossier: it has no {SCHEMA_KEY}")
    if plain[SCHEMA_KEY] == DOSSIER_SCHEMA_VERSION:
        return None
    if plain[SCHEMA_KEY] != PREVIOUS_VERSION:
        raise MigrationFailed(f"has {SCHEMA_KEY} {plain[SCHEMA_KEY]!r}; only {PREVIOUS_VERSION} migrates")
    rewritten, count = VERSION_FIELD.subn(rf"\g<1>{DOSSIER_SCHEMA_VERSION}", text, count=1)
    if count != 1 or json.loads(rewritten) != plain | {SCHEMA_KEY: DOSSIER_SCHEMA_VERSION}:
        raise MigrationFailed(f"its {SCHEMA_KEY} could not be rewritten alone")
    return rewritten


def migrate_files(paths: Sequence[Path]) -> Migrated:
    planned = {path: _migrated_file(path) for path in paths}
    for path, text in planned.items():
        if text is not None:
            write_text_atomically(path, text)
    return Migrated(
        rewritten=tuple(path for path, text in planned.items() if text is not None),
        current=tuple(path for path, text in planned.items() if text is None),
    )


def _migrated_file(path: Path) -> str | None:
    try:
        return migrated_text(path.read_text(encoding="utf-8"))
    except (MigrationFailed, json.JSONDecodeError) as failure:
        raise MigrationFailed(f"{relative_label(path)}: {failure}") from None


def main(argv: Sequence[str] | None = None) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(
        description=f"Rewrite dossiers of schema {PREVIOUS_VERSION} as schema {DOSSIER_SCHEMA_VERSION}, "
        f"changing {SCHEMA_KEY} alone."
    )
    parser.add_argument("dossiers", nargs="*", type=Path, help="dossiers to migrate (default: every dossier)")
    parser.add_argument("--dir", type=Path, default=CURATION_DIR, help="the curation directory")
    options = parser.parse_args(argv)
    paths = options.dossiers or [*dossier_paths(options.dir), *category_paths(options.dir)]
    try:
        outcome = migrate_files(paths)
    except MigrationFailed as failure:
        print(failure)
        return 1
    for path in outcome.rewritten:
        print(f"{relative_label(path)}: schema {DOSSIER_SCHEMA_VERSION}")
    print(f"migrated {len(outcome.rewritten)}, already current {len(outcome.current)}")
    return 0
