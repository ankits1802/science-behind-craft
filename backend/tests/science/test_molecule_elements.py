import json
import re
from pathlib import Path

import pytest

from app.science.molecule_conformer import DRAWN_ELEMENTS, conformer_geometry
from app.science.molecule_drawing import ATOM_RADII, LETTERED
from app.science.molecule_elements import ELEMENTS, atom_token, key_label, model_margin

from ..compose.held import IRON_OXIDE

BACKEND = Path(__file__).resolve().parents[2]
TOKENS = BACKEND / "app" / "data" / "design" / "tokens.json"
KIT_JS = BACKEND / "app" / "data" / "monographs" / "kit" / "monograph.js"
KIT_RADII = re.compile(r"var RAD = \{(?P<body>[^}]*)\};")
PAIR = re.compile(r"(?P<symbol>[A-Z][a-z]?): (?P<radius>[\d.]+)")
HELD = ("S", "Cl", "Fe", "Cu", "Al", "Ca", "Na", "K", "Cr", "Sn", "Zn", "Ag", "Au", "Pb", "Ti", "Hg")


def test_the_drawn_elements_are_the_atoms_the_design_generator_colours() -> None:
    atoms = json.loads(TOKENS.read_text(encoding="utf-8"))["molecule"]["atoms"]
    assert [
        (symbol, entry["name"], entry["radius"], entry["lettered"]) for symbol, entry in atoms.items()
    ] == [(element.symbol, element.name, element.radius, element.lettered) for element in ELEMENTS.values()]
    assert DRAWN_ELEMENTS[:4] == ("C", "H", "N", "O")
    assert set(HELD) <= set(DRAWN_ELEMENTS)
    assert all(entry["cssVar"] == atom_token(symbol) for symbol, entry in atoms.items())


def test_carbon_hydrogen_nitrogen_and_oxygen_keep_the_approved_kit_s_radii_and_letters() -> None:
    assert {symbol: ATOM_RADII[symbol] for symbol in ("C", "H", "N", "O")} == {
        "C": 0.38,
        "H": 0.2,
        "N": 0.36,
        "O": 0.36,
    }
    assert frozenset(DRAWN_ELEMENTS) - {"C", "H"} == LETTERED
    assert (ATOM_RADII["S"], ATOM_RADII["Cl"], ATOM_RADII["Fe"], ATOM_RADII["K"]) == (0.53, 0.51, 0.55, 0.55)


def test_the_kit_turns_each_atom_at_the_radius_the_server_draws_it() -> None:
    found = KIT_RADII.search(KIT_JS.read_text(encoding="utf-8"))
    assert found is not None
    radii = {pair.group("symbol"): float(pair.group("radius")) for pair in PAIR.finditer(found.group("body"))}
    assert radii == dict(ATOM_RADII)


@pytest.mark.parametrize(
    ("symbol", "label"),
    [("C", "Carbon"), ("H", "Hydrogen"), ("N", "Nitrogen, N"), ("Fe", "Iron, Fe"), ("S", "Sulphur, S")],
)
def test_a_key_names_each_element_and_the_letter_its_sphere_carries(symbol: str, label: str) -> None:
    assert key_label(symbol) == label


def test_a_model_keeps_room_round_its_largest_atom_and_an_organic_one_its_approved_margin() -> None:
    assert model_margin(["C", "H", "O"]) == 0.42
    assert model_margin(["S", "O"]) == 0.57
    assert model_margin(["Fe", "O"]) == 0.59
    assert model_margin(["Si", "O"]) == 0.42
    assert conformer_geometry(IRON_OXIDE).radius == 1.39
