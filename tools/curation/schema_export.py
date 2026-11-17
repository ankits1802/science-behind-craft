from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.curation.dossier import dossier_schema_text

from .output import REPO_ROOT, relative_label, write_text_atomically

__all__ = ["SCHEMA_PATH", "main"]

SCHEMA_PATH = REPO_ROOT / "shared" / "curation.dossier.schema.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the dossier JSON Schema generated from the Pydantic model."
    )
    parser.parse_args(argv)
    write_text_atomically(SCHEMA_PATH, dossier_schema_text())
    print(f"wrote {relative_label(SCHEMA_PATH)}")
    return 0
