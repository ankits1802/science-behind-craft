import json
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.component_specs_science_geometry import MoleculeGeometry
from app.research.drawing_rules import text_floor
from app.science.molecule_conformer import conformer_geometry, hill_formula, undrawn_elements
from app.science.molecule_drawing import molecule_drawing

from ..compose.held import SILICA

BACKEND = Path(__file__).resolve().parents[2]
SDF = (BACKEND / "tests" / "sources" / "fixtures" / "pubchem_conformer.sdf").read_text(encoding="ascii")
AJRAKH = BACKEND / "app" / "data" / "monographs" / "Kutch-Ajrakh"
ALIZARIN_CID = "6293"
LETTER_FLOOR = text_floor(2.0)


def ajrakh_data() -> dict[str, Any]:
    content = json.loads((AJRAKH / "content.json").read_text(encoding="utf-8"))
    return content["data"]["mol-data"][ALIZARIN_CID]


def ajrakh_model() -> dict[str, Any]:
    spec = json.loads(
        (AJRAKH / "specs" / "shared__chemistry__alizarin-purpurin-3d.json").read_text(encoding="utf-8")
    )
    return next(model for model in spec["molecules"] if model["cid"] == int(ALIZARIN_CID))


def test_pubchem_s_recorded_conformer_gives_the_geometry_kutch_ajrakh_s_page_turns() -> None:
    geometry = conformer_geometry(SDF)
    held = ajrakh_data()
    assert [list(atom) for atom in geometry.atoms] == held["atoms"]
    assert [list(bond) for bond in geometry.bonds] == held["bonds"]
    assert geometry.radius == held["R"]
    assert hill_formula(geometry) == "C14H8O4"
    assert undrawn_elements(geometry) == []


def unlettered(node: dict[str, Any]) -> dict[str, Any]:
    children = [unlettered(child) for child in node.get("children", []) if isinstance(child, dict)]
    kept = [child for child in children if child["tag"] != "text"]
    return {"tag": node["tag"], "attrs": node.get("attrs", {}), "children": kept}


def test_the_drawing_at_rest_is_the_one_kutch_ajrakh_s_page_draws_its_letters_kept_legible() -> None:
    model = ajrakh_model()
    geometry = MoleculeGeometry.model_validate(
        {"atoms": ajrakh_data()["atoms"], "bonds": ajrakh_data()["bonds"], "radius": ajrakh_data()["R"]}
    )
    drawn = molecule_drawing(geometry, yaw=model["yaw"], pitch=model["pitch"])
    assert unlettered(drawn) == unlettered(model["drawing"])
    letters = [
        child
        for atom in drawn["children"][0]["children"]
        for child in atom.get("children", [])
        if child["tag"] == "text"
    ]
    assert {letter["children"][0] for letter in letters} == {"O"}
    assert all(float(letter["attrs"]["font-size"]) >= LETTER_FLOOR for letter in letters)


def test_a_model_turned_by_nothing_lies_flat_and_hand_measured() -> None:
    geometry = MoleculeGeometry(
        atoms=[("O", 1.0, 0.0, 0.0), ("H", 0.0, 1.0, 0.0)], bonds=[(0, 1, 1)], radius=2.0
    )
    drawn = molecule_drawing(geometry, yaw=0.0, pitch=0.0)
    bond, oxygen, hydrogen = drawn["children"][0]["children"]
    assert oxygen["children"][0]["attrs"] == {
        "cx": "0.475",
        "cy": "0",
        "r": "0.171",
        "fill": "url(#ag-O)",
        "stroke": "var(--mol-edge)",
        "stroke-width": "0.005",
    }
    assert oxygen["children"][1]["attrs"]["font-size"] == "0.197"
    assert hydrogen["children"] == [
        {
            "tag": "circle",
            "attrs": {
                "cx": "0",
                "cy": "-0.475",
                "r": "0.095",
                "fill": "url(#ag-H)",
                "stroke": "var(--mol-edge)",
                "stroke-width": "0.005",
            },
        }
    ]
    assert bond["attrs"]["d"] == "M0.475 0L0 -0.475" and bond["attrs"]["stroke-width"] == "0.052"


def test_an_element_the_design_has_no_atom_colour_for_is_named_and_a_v3000_file_is_refused() -> None:
    assert undrawn_elements(conformer_geometry(SILICA)) == ["Si"]
    with pytest.raises(InvalidInput, match="V2000"):
        conformer_geometry(SDF.replace("V2000", "V3000"))
    with pytest.raises(InvalidInput, match="ends before"):
        conformer_geometry("\n".join(SDF.split("\n")[:10]))
