from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from typing import Annotated, Self

from pydantic import Field, model_validator

from .component_specs_science_parts import SpecModel, SvgNode

__all__ = [
    "ATOMS_MAX",
    "ATOM_MARK",
    "BONDS_MAX",
    "BOND_MARK",
    "MOLECULE_GROUP",
    "MoleculeGeometry",
    "geometry_drawing_problem",
]

ATOMS_MAX = 200
BONDS_MAX = 240
ATOM_SYMBOL = r"^[A-Z][a-z]?$"
MOLECULE_GROUP = "mol-g"
ATOM_MARK, BOND_MARK = "data-a", "data-b"
CLASS = "class"

AtomSymbol = Annotated[str, Field(pattern=ATOM_SYMBOL)]
AtomIndex = Annotated[int, Field(ge=0)]
BondOrder = Annotated[int, Field(ge=1, le=3)]


class MoleculeGeometry(SpecModel):
    atoms: list[tuple[AtomSymbol, float, float, float]] = Field(min_length=1, max_length=ATOMS_MAX)
    bonds: list[tuple[AtomIndex, AtomIndex, BondOrder]] = Field(default_factory=list, max_length=BONDS_MAX)
    radius: float = Field(gt=0)

    @model_validator(mode="after")
    def _bonds_join_its_atoms(self) -> Self:
        for first, second, _ in self.bonds:
            if first == second or max(first, second) >= len(self.atoms):
                raise ValueError(
                    f"the bond {first}-{second} does not join two of the {len(self.atoms)} atoms"
                )
        return self


def geometry_drawing_problem(drawing: SvgNode, geometry: MoleculeGeometry) -> str | None:
    groups = [node for node in _nodes(drawing) if MOLECULE_GROUP in node.attrs.get(CLASS, "").split()]
    if len(groups) != 1:
        return f"a model with its geometry draws one <g class={MOLECULE_GROUP!r}>, the group the page turns"
    marks = [child for child in groups[0].children if isinstance(child, SvgNode)]
    atoms = Counter(child.attrs[ATOM_MARK] for child in marks if ATOM_MARK in child.attrs)
    bonds = Counter(child.attrs[BOND_MARK] for child in marks if BOND_MARK in child.attrs)
    if atoms != Counter(str(at) for at in range(len(geometry.atoms))):
        return f"the group marks each of the {len(geometry.atoms)} atoms once, as {ATOM_MARK}"
    if bonds != Counter(str(at) for at in range(len(geometry.bonds))):
        return f"the group marks each of the {len(geometry.bonds)} bonds once, as {BOND_MARK}"
    return None


def _nodes(node: SvgNode) -> Iterator[SvgNode]:
    yield node
    for child in node.children:
        if isinstance(child, SvgNode):
            yield from _nodes(child)
