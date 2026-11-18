from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType
from typing import Any

from .craft_master_loader import DATA_DIR
from .district_register import load_district_register

__all__ = [
    "STATE_LANGUAGES_FILE",
    "STATE_LANGUAGES_SCHEMA_VERSION",
    "load_state_languages",
    "parse_state_languages",
]

STATE_LANGUAGES_FILE = DATA_DIR / "state_languages.json"
STATE_LANGUAGES_SCHEMA_VERSION = 1
LANGUAGE_CODE = re.compile(r"^[a-z]{2,3}$")


def parse_state_languages(raw: Mapping[str, Any], states: frozenset[str]) -> Mapping[str, tuple[str, ...]]:
    if raw.get("schemaVersion") != STATE_LANGUAGES_SCHEMA_VERSION:
        raise ValueError(f"state languages need schemaVersion {STATE_LANGUAGES_SCHEMA_VERSION}")
    listed: Mapping[str, Any] = raw.get("states") or {}
    if set(listed) != states:
        named = sorted(set(listed) ^ states)
        raise ValueError(f"state languages must list every LGD state exactly; differs at {', '.join(named)}")
    languages: dict[str, tuple[str, ...]] = {}
    for state, codes in listed.items():
        found = tuple(str(code) for code in codes)
        if len(set(found)) != len(found) or not all(LANGUAGE_CODE.fullmatch(code) for code in found):
            raise ValueError(f"the languages of {state} are not distinct ISO 639 codes")
        languages[state] = found
    return MappingProxyType(languages)


@lru_cache(maxsize=1)
def load_state_languages() -> Mapping[str, tuple[str, ...]]:
    raw = json.loads(STATE_LANGUAGES_FILE.read_text(encoding="utf-8"))
    return parse_state_languages(raw, load_district_register().states)
