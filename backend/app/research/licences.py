from __future__ import annotations

import re

__all__ = ["OPEN_LICENCE_NAMES", "OPEN_LICENCE_URL_PREFIXES", "open_licence"]

OPEN_LICENCE_NAMES = frozenset(
    {
        "cc0",
        "cc zero",
        "cc by",
        "cc by sa",
        "pddl",
        "pd",
        "public domain",
        "public domain mark",
        "creative commons zero",
        "creative commons attribution",
        "creative commons attribution sharealike",
        "creative commons attribution share alike",
        "open data commons public domain dedication and license",
    }
)
OPEN_LICENCE_URL_PREFIXES = (
    "creativecommons.org/licenses/by/",
    "creativecommons.org/licenses/by-sa/",
    "creativecommons.org/publicdomain/zero/",
    "creativecommons.org/publicdomain/mark/",
    "opendatacommons.org/licenses/pddl/",
)
URL_START = re.compile(r"^(?:https?://)?(?:www\.)?")
NAME_SEPARATORS = re.compile(r"[\s\-_/,()]+")
TRAILING_WORDS = frozenset(
    {"international", "unported", "generic", "universal", "igo", "license", "licence", "deed"}
)
VERSION = re.compile(r"^v?\d+(?:\.\d+)*$")


def open_licence(licence: str | None) -> bool:
    text = (licence or "").strip().casefold()
    if not text:
        return False
    if "://" in text or text.startswith(("www.", "creativecommons.org", "opendatacommons.org")):
        return _open_url(text)
    return _licence_name(text) in OPEN_LICENCE_NAMES


def _open_url(text: str) -> bool:
    path = URL_START.sub("", text).split("?", 1)[0].split("#", 1)[0]
    path = path if path.endswith("/") else f"{path}/"
    return path.startswith(OPEN_LICENCE_URL_PREFIXES)


def _licence_name(text: str) -> str:
    words = [word for word in NAME_SEPARATORS.split(text) if word]
    while words and (words[-1] in TRAILING_WORDS or VERSION.match(words[-1])):
        words.pop()
    return " ".join(words)
