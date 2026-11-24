from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

__all__ = [
    "AGENT_ROLES",
    "DEPICTED_COLOURS",
    "KEY_COLOURS_MIN",
    "DepictedColour",
    "depicted_material",
    "named_substances",
]

KEY_COLOURS_MIN = 2
AGENT_ROLES = frozenset({"DYE", "MORDANT", "RESIST"})
WORDS = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class DepictedColour:
    colour: str
    substances: tuple[str, ...]


DEPICTED_COLOURS: Mapping[str, DepictedColour] = MappingProxyType(
    {
        "indigo": DepictedColour("BLUE", ("indigo", "indigotin", "indigofera", "neel")),
        "leuco": DepictedColour("GREEN", ("indigo", "leucoindigo", "indigofera")),
        "madder": DepictedColour("RED", ("madder", "manjistha", "majeeta", "rubia", "alizarin")),
        "pink": DepictedColour("PINK", ("madder", "manjistha", "majeeta", "rubia", "alizarin")),
        "harda": DepictedColour(
            "YELLOW", ("harda", "harad", "harde", "hirda", "myrobalan", "terminalia chebula")
        ),
        "kut": DepictedColour(
            "BLACK",
            (
                "kut",
                "ferrous sulphate",
                "ferrous sulfate",
                "ferrous acetate",
                "iron acetate",
                "scrap iron",
                "iron scrap",
                "iron filings",
            ),
        ),
        "lime": DepictedColour("WHITE", ("lime", "chuna")),
        "kesari": DepictedColour("ORANGE", ("kesari",)),
        "mud": DepictedColour("BROWN", ("gach", "dabu", "mud")),
        "cobalt": DepictedColour("BLUE", ("cobalt",)),
        "quartz-white": DepictedColour("WHITE", ("quartz",)),
        "sem-green": DepictedColour("GREEN", ("sem",)),
    }
)


def named_substances(names: Iterable[str]) -> str:
    return " " + " | ".join(" ".join(WORDS.findall(name.casefold())) for name in names) + " "


def depicted_material(colour: str | None, names: Iterable[str]) -> str | None:
    if colour is None:
        return None
    named = named_substances(names)
    for token, depicted in DEPICTED_COLOURS.items():
        if depicted.colour == colour and any(f" {substance} " in named for substance in depicted.substances):
            return token
    return None
