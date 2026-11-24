from __future__ import annotations

from typing import Any

from design.colour import contrast, delta_e, fmt_oklch, hex_to_rgb
from design.system import System, mix

__all__ = ["ATOM_PREFIX", "atom_list", "edge_css", "molecule_css", "molecule_tokens"]

ATOM_PREFIX = "--atom-"
EDGE = "mol-edge"


def edge_css(colour: str, alpha: float) -> str:
    red, green, blue = (round(value * 255) for value in hex_to_rgb(colour))
    return f"rgb({red} {green} {blue} / {alpha})"


def _edge(system: System, theme: str) -> dict[str, Any]:
    colour, alpha = system.data["molecule"]["edge"][theme]
    stage = system.sem(system.data["molecule"]["stage"], theme)
    return {"css": edge_css(colour, alpha), "onStage": mix(colour, stage, alpha)}


def _kit_entry(system: System, row: list[Any]) -> dict[str, Any]:
    name, use, *values = row
    stage = system.data["molecule"]["stage"]
    entry: dict[str, Any] = {"cssVar": f"--{name}", "use": use}
    for theme, colour in zip(system.themes, values, strict=True):
        entry[theme] = {"hex": colour, "vsStage": round(contrast(colour, system.sem(stage, theme)), 2)}
    return entry


def _atom_theme(system: System, colour: str, theme: str, lettered: bool) -> dict[str, Any]:
    stage = system.sem(system.data["molecule"]["stage"], theme)
    edge = _edge(system, theme)["onStage"]
    gap, token = system.reserved_min(colour, theme)
    entry: dict[str, Any] = {
        "hex": colour,
        "oklch": fmt_oklch(colour),
        "vsStage": round(contrast(colour, stage), 2),
        "vsEdge": round(contrast(colour, edge), 2),
        "nearestSemantic": {"deltaE": gap, "token": token},
    }
    if lettered:
        letter = _letter(system, theme)
        entry["vsLetter"] = round(contrast(colour, letter), 2)
    return entry


def _letter(system: System, theme: str) -> str:
    for name, _, *values in system.data["molecule"]["kit"]:
        if name == "mol-letter":
            return str(values[system.theme_index(theme)])
    raise KeyError("mol-letter")


def _atoms(system: System) -> dict[str, Any]:
    atoms: dict[str, Any] = {}
    for symbol, name, radius, lettered, *values in system.data["molecule"]["atoms"]:
        entry: dict[str, Any] = {
            "cssVar": f"{ATOM_PREFIX}{symbol.lower()}",
            "name": name,
            "radius": radius,
            "lettered": lettered,
        }
        for theme, colour in zip(system.themes, values, strict=True):
            entry[theme] = _atom_theme(system, colour, theme, lettered)
        atoms[symbol] = entry
    for theme in system.themes:
        for symbol, entry in atoms.items():
            gap, nearest = min(
                (round(delta_e(entry[theme]["hex"], other[theme]["hex"]), 1), key)
                for key, other in atoms.items()
                if key != symbol
            )
            entry[theme]["nearestAtom"] = {"deltaE": gap, "symbol": nearest}
    return atoms


def molecule_tokens(system: System) -> dict[str, Any]:
    molecule = system.data["molecule"]
    kit = {row[0]: _kit_entry(system, row) for row in molecule["kit"]}
    kit[EDGE] = {
        "cssVar": f"--{EDGE}",
        "use": molecule["edge"]["use"],
        **{theme: _edge(system, theme) for theme in system.themes},
    }
    return {"rule": molecule["rule"], "stage": molecule["stage"], "kit": kit, "atoms": _atoms(system)}


def molecule_css(tokens: dict[str, Any], theme: str) -> list[str]:
    molecule = tokens["molecule"]
    atoms = " ".join(f"{entry['cssVar']}: {entry[theme]['hex']};" for entry in molecule["atoms"].values())
    kit = " ".join(
        f"{entry['cssVar']}: {entry[theme]['css'] if name == EDGE else entry[theme]['hex']};"
        for name, entry in molecule["kit"].items()
    )
    return [atoms, kit]


def atom_list(tokens: dict[str, Any]) -> str:
    rows = "".join(
        f'    ("{symbol}", "{entry["name"]}", {entry["radius"]}, {entry["lettered"]}),\n'
        for symbol, entry in tokens["molecule"]["atoms"].items()
    )
    return f'__all__ = ["MOLECULE_ATOMS"]\n\nMOLECULE_ATOMS = (\n{rows})\n'
