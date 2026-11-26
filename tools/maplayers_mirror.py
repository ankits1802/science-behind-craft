from __future__ import annotations

import argparse
import sys
from pathlib import Path

from maplayers.mirror import mirror_base

REPO_ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = (
    "Mirror the base the API draws its paper maps on into backend/app/data/layers: the Survey of India "
    "outline the web map draws and the state lines it draws over it. The map layers build mirrors them "
    "too; run this alone when either changes."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT, help="repository root to read from and write into"
    )
    options = parser.parse_args(argv)
    for path in mirror_base(options.root):
        print(f"{path.as_posix()} mirrored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
