import copy
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.component_specs_science import SPEC_MODELS_SCIENCE
from app.research.drawing_spec_rules import spec_design_problems

from .science_spec_fixtures import molecule_3d

MOLECULE = SPEC_MODELS_SCIENCE["molecule_3d"]
ATOMS = [["O", 1.0, 0.0, 0.0], ["H", 0.0, 1.0, 0.0]]


def drawn(*children: dict[str, Any]) -> dict[str, Any]:
    group = {"tag": "g", "attrs": {"class": "mol-g"}, "children": list(children)}
    return {"tag": "svg", "attrs": {"viewBox": "-1 -1 2 2"}, "children": [group]}


def atom(index: int) -> dict[str, Any]:
    return {
        "tag": "g",
        "attrs": {"data-a": str(index)},
        "children": [{"tag": "circle", "attrs": {"r": "0.1"}}],
    }


def bond(index: int) -> dict[str, Any]:
    return {"tag": "path", "attrs": {"data-b": str(index), "d": "M0 0L1 1"}}


def with_geometry(drawing: dict[str, Any], **geometry: Any) -> dict[str, Any]:
    spec = copy.deepcopy(molecule_3d())
    model = spec["molecules"][0]
    model["drawing"] = drawing
    model["geometry"] = {"atoms": ATOMS, "bonds": [[0, 1, 1]], "radius": 1.42} | geometry
    return spec


def test_a_model_with_its_geometry_draws_each_atom_and_bond_once_in_the_group_the_page_turns() -> None:
    spec = with_geometry(drawn(bond(0), atom(0), atom(1)))
    assert MOLECULE.model_validate(spec).model_dump(mode="json", by_alias=True) == spec
    assert (
        "geometry"
        not in MOLECULE.model_validate(molecule_3d()).model_dump(mode="json", by_alias=True)["molecules"][0]
    )


@pytest.mark.parametrize(
    "spec",
    [
        with_geometry(drawn(atom(0), atom(1))),
        with_geometry(drawn(bond(0), atom(0))),
        with_geometry(drawn(bond(0), atom(0), atom(0), atom(1))),
        with_geometry(
            {"tag": "svg", "attrs": {"viewBox": "-1 -1 2 2"}, "children": [atom(0), atom(1), bond(0)]}
        ),
        with_geometry(drawn(bond(0), atom(0), atom(1)), bonds=[[0, 2, 1]]),
        with_geometry(drawn(bond(0), atom(0), atom(1)), bonds=[[0, 1, 4]]),
        with_geometry(drawn(bond(0), atom(0), atom(1)), atoms=[["o", 0.0, 0.0, 0.0], ["H", 1.0, 0.0, 0.0]]),
        with_geometry(drawn(bond(0), atom(0), atom(1)), radius=0),
    ],
    ids=[
        "no bond",
        "an atom missing",
        "an atom twice",
        "no group",
        "a bond past the atoms",
        "a fourth order",
        "a lower-case element",
        "no radius",
    ],
)
def test_a_geometry_the_drawing_or_its_atoms_contradict_is_refused(spec: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        MOLECULE.model_validate(spec)


def test_a_molecule_s_key_shows_its_atom_colours_and_a_species_swatch_still_shows_a_material() -> None:
    assert spec_design_problems({"key": [{"swatch": "--atom-c", "label": "Carbon"}]}) == []
    found = spec_design_problems({"items": [{"swatch": "--atom-c"}]})
    assert found == [
        "items[0].swatch names --atom-c; a swatch or dip shows a depicted --dye-* or --dip-* material"
    ]
