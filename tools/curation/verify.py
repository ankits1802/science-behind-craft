from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    TOOLS = Path(__file__).resolve().parents[1]
    sys.path[0:1] = [str(TOOLS), str(TOOLS.parent / "backend")]
    from curation.verifying import main

    sys.exit(main())
