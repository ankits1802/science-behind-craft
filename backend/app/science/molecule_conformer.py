from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from app.core.errors import InvalidInput
from app.research.component_specs_science_geometry import ATOMS_MAX, BONDS_MAX, MoleculeGeometry

__all__ = [
    "DRAWN_ELEMENTS",
    "RADIUS_MARGIN",
    "conformer_geometry",
    "element_counts",
    "hill_formula",
    "undrawn_elements",
]

COUNTS_LINE = 3
MOLFILE_V2000 = "V2000"
ATOM_FIELDS = (slice(0, 10), slice(10, 20), slice(20, 30))
SYMBOL_FIELD = slice(31, 34)
BOND_FIELDS = (slice(0, 3), slice(3, 6), slice(6, 9))
COUNT_FIELDS = (slice(0, 3), slice(3, 6))
BOND_ORDERS = frozenset({1, 2, 3})
COORDINATE_DECIMALS = 4
RADIUS_DECIMALS = 3
RADIUS_MARGIN = 0.42
DRAWN_ELEMENTS = ("C", "H", "N", "O")
HILL_FIRST = ("C", "H")

Atom = tuple[str, float, float, float]
Bond = tuple[int, int, int]


def conformer_geometry(sdf: str) -> MoleculeGeometry:
    lines = sdf.split("\n")
    if len(lines) <= COUNTS_LINE or MOLFILE_V2000 not in lines[COUNTS_LINE]:
        raise InvalidInput("the conformer is not a V2000 molfile")
    atom_count, bond_count = (_whole(lines[COUNTS_LINE][field]) for field in COUNT_FIELDS)
    if not 0 < atom_count <= ATOMS_MAX or bond_count > BONDS_MAX:
        raise InvalidInput(
            f"the conformer holds {atom_count} atoms and {bond_count} bonds, where a 3D model draws one to "
            f"{ATOMS_MAX} atoms and at most {BONDS_MAX} bonds"
        )
    first = COUNTS_LINE + 1
    block = lines[first : first + atom_count + bond_count]
    if len(block) != atom_count + bond_count:
        raise InvalidInput("the conformer ends before its atoms and bonds")
    atoms = [_atom(line) for line in block[:atom_count]]
    bonds = [_bond(line, atom_count) for line in block[atom_count:]]
    return _centred(atoms, bonds)


def element_counts(geometry: MoleculeGeometry) -> Counter[str]:
    return Counter(atom[0] for atom in geometry.atoms)


def hill_formula(geometry: MoleculeGeometry) -> str:
    counts = element_counts(geometry)
    carbon = "C" in counts
    order = [*HILL_FIRST, *sorted(set(counts) - set(HILL_FIRST))] if carbon else sorted(counts)
    return "".join(
        f"{symbol}{counts[symbol] if counts[symbol] > 1 else ''}" for symbol in order if symbol in counts
    )


def undrawn_elements(geometry: MoleculeGeometry) -> list[str]:
    return sorted(set(element_counts(geometry)) - set(DRAWN_ELEMENTS))


def _centred(atoms: Sequence[Atom], bonds: Sequence[Bond]) -> MoleculeGeometry:
    if not atoms:
        raise InvalidInput("the conformer holds no atoms")
    count = len(atoms)
    cx, cy, cz = (math.fsum(atom[axis] for atom in atoms) / count for axis in (1, 2, 3))
    moved = [(symbol, x - cx, y - cy, z - cz) for symbol, x, y, z in atoms]
    reach = max(math.sqrt(x * x + y * y + z * z) for _, x, y, z in moved)
    return MoleculeGeometry(
        atoms=[(symbol, _rounded(x), _rounded(y), _rounded(z)) for symbol, x, y, z in moved],
        bonds=list(bonds),
        radius=round(reach + RADIUS_MARGIN, RADIUS_DECIMALS),
    )


def _rounded(value: float) -> float:
    return round(value, COORDINATE_DECIMALS)


def _atom(line: str) -> Atom:
    symbol = line[SYMBOL_FIELD].strip()
    if not symbol:
        raise InvalidInput(f"the conformer's atom line {line.strip()!r} names no element")
    x, y, z = (_coordinate(line[field]) for field in ATOM_FIELDS)
    return symbol, x, y, z


def _bond(line: str, atom_count: int) -> Bond:
    first, second, order = (_whole(line[field]) for field in BOND_FIELDS)
    if order not in BOND_ORDERS or not (1 <= first <= atom_count and 1 <= second <= atom_count):
        raise InvalidInput(
            f"the conformer's bond line {line.strip()!r} is not a single, double or triple bond"
        )
    return first - 1, second - 1, order


def _whole(field: str) -> int:
    try:
        return int(field)
    except ValueError:
        raise InvalidInput(f"the conformer holds {field!r} where a count belongs") from None


def _coordinate(field: str) -> float:
    try:
        return float(field)
    except ValueError:
        raise InvalidInput(f"the conformer holds {field!r} where a coordinate belongs") from None
