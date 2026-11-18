from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

__all__ = [
    "COLOUR_SIDES",
    "COLOUR_SURFACES",
    "COLOUR_WORDS",
    "ColourSide",
    "ColourWord",
    "colour_of",
    "states_colour",
]

COLOUR_SURFACES: Mapping[str, str] = MappingProxyType(
    {
        "red": "RED",
        "blue": "BLUE",
        "black": "BLACK",
        "white": "WHITE",
        "green": "GREEN",
        "yellow": "YELLOW",
        "brown": "BROWN",
        "grey": "GREY",
        "gray": "GREY",
        "pink": "PINK",
        "purple": "PURPLE",
        "orange": "ORANGE",
        "maroon": "MAROON",
    }
)
COLOUR_WORDS = tuple(dict.fromkeys(COLOUR_SURFACES.values()))
COLOUR_SIDES = ("BEFORE", "AFTER")
WORDS = re.compile(r"[a-z]+")

ColourWord = Literal[*COLOUR_WORDS]
ColourSide = Literal[*COLOUR_SIDES]


def colour_of(word: str) -> str | None:
    parts = WORDS.findall(word.casefold())
    return COLOUR_SURFACES.get(parts[-1]) if parts else None


def states_colour(stated: str, colour: str) -> bool:
    return any(COLOUR_SURFACES.get(word) == colour for word in WORDS.findall(stated.casefold()))
