from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

__all__ = [
    "AGENT_ROLES",
    "DEPICTED_COLOURS",
    "KEY_COLOURS_MIN",
    "SPECIMEN_PREFIX",
    "AgentMaterial",
    "DepictedColour",
    "agent_materials",
    "agent_names",
    "depicted_material",
    "first_depicted",
    "named_substances",
    "specimen_token",
]

KEY_COLOURS_MIN = 2
AGENT_ROLES = frozenset({"DYE", "MORDANT", "RESIST"})
SPECIMEN_PREFIX = "--dye-"
WORDS = re.compile(r"[a-z]+")
IRON_BLACK = (
    "kut",
    "syahi",
    "syahee",
    "kasim",
    "kasam",
    "ferrous sulphate",
    "ferrous sulfate",
    "ferrous acetate",
    "iron acetate",
    "scrap iron",
    "iron scrap",
    "iron filings",
)
MADDER = ("madder", "manjistha", "majeeta", "rubia", "alizarin")


class AgentMaterial(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def role(self) -> str | None: ...
    @property
    def botanical_name(self) -> str | None: ...
    @property
    def local_names(self) -> Sequence[str]: ...


@dataclass(frozen=True)
class DepictedColour:
    colour: str
    substances: tuple[str, ...]


DEPICTED_COLOURS: Mapping[str, DepictedColour] = MappingProxyType(
    {
        "indigo": DepictedColour("BLUE", ("indigo", "indigotin", "indigofera", "neel")),
        "leuco": DepictedColour("GREEN", ("indigo", "leucoindigo", "indigofera")),
        "madder": DepictedColour("RED", MADDER),
        "pink": DepictedColour("PINK", MADDER),
        "harda": DepictedColour(
            "YELLOW", ("harda", "harad", "harde", "hirda", "myrobalan", "terminalia chebula")
        ),
        "turmeric": DepictedColour("YELLOW", ("turmeric", "haldi", "haldar", "curcuma")),
        "pomegranate": DepictedColour(
            "YELLOW", ("pomegranate", "naspal", "dadam", "anar", "punica granatum")
        ),
        "orpiment": DepictedColour("YELLOW", ("orpiment", "haritala", "hartala", "harital")),
        "kut": DepictedColour("BLACK", IRON_BLACK),
        "kali-mitti": DepictedColour("BLACK", ("kali mitti", "black clay")),
        "lamp-black": DepictedColour("BLACK", ("lamp black", "lampblack", "lamp soot")),
        "lime": DepictedColour("WHITE", ("lime", "chuna")),
        "conch-white": DepictedColour("WHITE", ("conch", "sankh", "sankha")),
        "kesari": DepictedColour("ORANGE", ("kesari",)),
        "mud": DepictedColour("BROWN", ("gach", "dabu", "mud")),
        "cinnabar": DepictedColour("RED", ("cinnabar", "hingula", "hengula", "hinglu")),
        "red-ochre": DepictedColour("RED", ("red ochre", "geru", "gerua", "gairika")),
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


def first_depicted(colours: Iterable[str], names: Sequence[str]) -> tuple[str, str] | None:
    for colour in colours:
        token = depicted_material(colour, names)
        if token is not None:
            return colour, token
    return None


def agent_materials[Agent: AgentMaterial](materials: Iterable[Agent]) -> list[Agent]:
    return [material for material in materials if material.role in AGENT_ROLES]


def agent_names(materials: Iterable[AgentMaterial]) -> tuple[str, ...]:
    return tuple(
        name
        for material in materials
        for name in (material.name, material.botanical_name, *material.local_names)
        if name
    )


def specimen_token(material: str) -> str:
    return f"{SPECIMEN_PREFIX}{material}"
