from __future__ import annotations

import copy
import re

from design.build import build, render
from design.build_molecule import atom_list, edge_css
from design.checks import validate
from design.system import System, load_system
from design_tokens import REPO_ROOT

SYSTEM = load_system()
OUTPUTS, VIOLATIONS = render(SYSTEM)
TOKENS = build(SYSTEM)
KIT_CSS = (REPO_ROOT / "backend" / "app" / "data" / "monographs" / "kit" / "monograph.css").read_text(
    encoding="utf-8"
)
KIT_RULES = {
    "light": r":root \.bx-chem\{(--atom-c:[^}]*)\}",
    "dark": r':root\[data-theme="dark"\] \.bx-chem\{(--atom-c:[^}]*)\}',
}
DECLARATION = re.compile(r"--(atom-[a-z]+|mol-[a-z]+):\s*([^;]+?)\s*(?:;|$)")
HELD = ("s", "cl", "fe", "cu", "al", "ca", "na", "k", "cr", "sn", "zn", "ag", "au", "pb", "ti", "hg")
THEME_BLOCKS = {
    "light": ":root {",
    "dark": ':root[data-theme="dark"] {',
    "hcLight": ':root[data-high-contrast="true"] {',
    "hcDark": ':root[data-theme="dark"][data-high-contrast="true"] {',
}


def _block(css: str, opening: str) -> str:
    start = css.index(opening)
    return css[start : css.index("}", start)]


def _with_atom(symbol: str, theme: str, colour: str) -> System:
    data = copy.deepcopy(SYSTEM.data)
    column = 4 + SYSTEM.theme_index(theme)
    for row in data["molecule"]["atoms"]:
        if row[0] == symbol:
            row[column] = colour
    return System(data, SYSTEM.materials)


def _violations(system: System) -> list[str]:
    return validate(build(system), system)


def _channels(value: str) -> list[float]:
    return [float(number) for number in re.findall(r"[\d.]+", value)]


def test_every_element_the_crafts_compounds_hold_has_its_atom_colour_in_all_four_themes() -> None:
    css = OUTPUTS["tokens.css"]
    for theme, opening in THEME_BLOCKS.items():
        block = _block(css, opening)
        for symbol in ("c", "h", "n", "o", *HELD):
            assert f"--atom-{symbol}: #" in block, (theme, symbol)
        assert "--mol-edge: rgb(" in block and "--mol-letter: #" in block, theme
    assert "--atom-fe: #8E3F34;" in _block(css, THEME_BLOCKS["light"])
    assert "--atom-fe: #C36953;" in _block(css, THEME_BLOCKS["dark"])
    assert VIOLATIONS == []


def test_the_kit_s_four_atoms_and_its_bond_edge_and_letter_are_the_generator_s() -> None:
    molecule = TOKENS["molecule"]
    for theme, rule in KIT_RULES.items():
        found = re.search(rule, KIT_CSS)
        assert found is not None, theme
        declared = dict(DECLARATION.findall(found.group(1)))
        for symbol in ("C", "H", "N", "O"):
            assert declared[f"atom-{symbol.lower()}"] == molecule["atoms"][symbol][theme]["hex"], (
                theme,
                symbol,
            )
        for name in ("mol-bond", "mol-letter"):
            assert declared[name] == molecule["kit"][name][theme]["hex"], (theme, name)
        assert _channels(declared["mol-edge"]) == _channels(molecule["kit"]["mol-edge"][theme]["css"])


def test_the_generator_lists_each_drawn_atom_for_the_server_with_its_name_radius_and_letter() -> None:
    listed = OUTPUTS["molecule_atoms.py"]
    assert listed.startswith('__all__ = ["MOLECULE_ATOMS"]')
    assert '    ("C", "carbon", 0.38, False),\n    ("H", "hydrogen", 0.2, False),\n' in listed
    assert '    ("Fe", "iron", 0.55, True),\n' in listed
    assert '    ("S", "sulphur", 0.53, True),\n' in listed
    assert atom_list(TOKENS) == listed
    assert edge_css("#1C1815", 0.55) == "rgb(28 24 21 / 0.55)"


def test_an_atom_as_close_as_another_atom_or_a_reserved_colour_is_refused() -> None:
    copper = SYSTEM.data["molecule"]["atoms"]
    (light_copper,) = [row[4] for row in copper if row[0] == "Cu"]
    assert "atom Fe light 0.0 from atom Cu" in _violations(_with_atom("Fe", "light", light_copper))
    terracotta = SYSTEM.sem("terracotta", "hcLight")
    assert "atom Fe hcLight 0.0 from terracotta" in _violations(_with_atom("Fe", "hcLight", terracotta))


def test_an_atom_whose_letter_or_edge_does_not_read_or_that_reads_as_indigo_is_refused() -> None:
    pale = _violations(_with_atom("Fe", "light", "#E8D9C0"))
    assert any(violation.startswith("atom Fe light letter ") for violation in pale)
    hidden = _violations(_with_atom("H", "light", "#A8A6A2"))
    assert any(violation.startswith("atom H light edge ") for violation in hidden)
    indigo = _violations(_with_atom("Cr", "light", SYSTEM.sem("indigo", "light")))
    assert "atom Cr light chroma" in " ".join(indigo) and "atom Cr light 0.0 from indigo" in indigo
