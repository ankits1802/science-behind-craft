from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.research.molecule_atoms import MOLECULE_ATOMS

__all__ = [
    "ATOM_PREFIX",
    "DRAWN_ELEMENTS",
    "ELEMENTS",
    "MARGIN_BEYOND",
    "RADIUS_MARGIN",
    "Element",
    "atom_token",
    "key_label",
    "model_margin",
]

ATOM_PREFIX = "--atom-"
RADIUS_MARGIN = 0.42
MARGIN_BEYOND = 0.04


@dataclass(frozen=True)
class Element:
    symbol: str
    name: str
    radius: float
    lettered: bool


ELEMENTS: Mapping[str, Element] = MappingProxyType(
    {symbol: Element(symbol, name, radius, lettered) for symbol, name, radius, lettered in MOLECULE_ATOMS}
)
DRAWN_ELEMENTS = tuple(ELEMENTS)


def atom_token(symbol: str) -> str:
    return f"{ATOM_PREFIX}{symbol.lower()}"


def key_label(symbol: str) -> str:
    element = ELEMENTS[symbol]
    named = element.name[:1].upper() + element.name[1:]
    return f"{named}, {symbol}" if element.lettered else named


def model_margin(symbols: Iterable[str]) -> float:
    largest = max((ELEMENTS[symbol].radius for symbol in symbols if symbol in ELEMENTS), default=0.0)
    return max(RADIUS_MARGIN, round(largest + MARGIN_BEYOND, 2))
