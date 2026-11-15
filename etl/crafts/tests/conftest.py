import sys
from pathlib import Path

ETL = Path(__file__).resolve().parents[1]
if str(ETL) not in sys.path:
    sys.path.insert(0, str(ETL))

import common  # noqa: E402, F401
