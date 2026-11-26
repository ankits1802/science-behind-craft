from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

__all__ = ["layer_text"]


def layer_text(body: Mapping[str, Any]) -> str:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n"
