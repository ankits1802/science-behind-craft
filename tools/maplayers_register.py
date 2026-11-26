from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = (
    "Read the site's river register into the built small-waters tiles again, without downloading "
    "OpenStreetMap: every river answers to the register's names where the two agree by name and district "
    "(the river names datasets, the dossiers' river places and the cited river aliases), and the API's "
    "names file follows. Run it when a dossier gains a river place or an alias is recorded."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT, help="repository root to read from and write into"
    )
    options = parser.parse_args(argv)
    sys.path.append(str(options.root / "backend"))
    from app.data.district_register import load_district_codes
    from app.data.river_aliases import load_river_aliases

    from maplayers.waters_names import reregister_files
    from maplayers.waters_register import site_register

    register = site_register(options.root, load_district_codes(), load_river_aliases())
    changed = reregister_files(options.root, register)
    print(f"{len(changed)} tiles renamed: {', '.join(changed) or 'none'}; the names file written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
