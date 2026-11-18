from __future__ import annotations

from itertools import pairwise
from typing import Any

from design.colour import contrast, delta_e, from_oklch, oklch
from design.cvd import cvd_delta_e
from design.system import System

__all__ = ["chart_tokens", "family_tokens", "map_tokens", "ramp_tokens"]

RAMP_MARKERS = {"ph": ("neutralVs", 2), "elevation": ("highestVs", -1)}
MAP_CONTRAST = {
    "map-coast": ("land", "water"),
    "map-border-state": ("land",),
    "map-border-intl": ("land",),
    "map-river": ("land",),
    "map-border-district": ("land",),
    "map-marker-ring": ("land",),
    "map-salt-hatch": ("salt",),
    "map-water-label": ("water",),
}
MAP_DELTA = {"map-water": ("land",), "map-salt": ("land", "water")}


def _on_page(system: System, colour: str, theme: str) -> dict[str, float]:
    return {
        "onGround": round(contrast(colour, system.sem("ground", theme)), 2),
        "onSunk": round(contrast(colour, system.sem("sunk", theme)), 2),
    }


def _series_entry(system: System, colour: str, theme: str) -> dict[str, Any]:
    gap, token = system.reserved_min(colour, theme)
    return {
        "hex": colour,
        **_on_page(system, colour, theme),
        "onLand": round(contrast(colour, system.map_colour("map-land", theme)), 2),
        "reservedMin": {"deltaE": gap, "token": token},
    }


def chart_tokens(system: System) -> dict[str, Any]:
    chart: dict[str, Any] = {}
    for name, kind, use, value in system.data["chart"]:
        token: dict[str, Any] = {"cssVar": f"--{name}", "class": kind, "use": use}
        for theme in system.themes:
            colour = system.resolve(value, theme)
            token[theme] = {"hex": colour, **_on_page(system, colour, theme)}
        chart[name] = token
    for name, (use, spec) in system.data["series"].items():
        token = {"cssVar": f"--{name}", "class": "graphic", "use": use}
        for theme in system.themes:
            token[theme] = _series_entry(system, from_oklch(*spec[theme]), theme)
        chart[name] = token
    return chart


def _ramp_steps(ramp: dict[str, Any], theme: str) -> list[str]:
    source = ramp[theme] if theme in ramp else ramp["spec"][theme]
    return [step if isinstance(step, str) else from_oklch(*step) for step in source]


def _ramp_surfaces(system: System, theme: str) -> dict[str, str]:
    return {
        "ground": system.sem("ground", theme),
        "sunk": system.sem("sunk", theme),
        "land": system.map_colour("map-land", theme),
        "foreign": system.map_colour("map-land-foreign", theme),
        "water": system.map_colour("map-water", theme),
    }


def _ramp_theme(system: System, key: str, steps: list[str], theme: str) -> dict[str, Any]:
    surfaces = _ramp_surfaces(system, theme)
    reserved = [system.reserved_min(step, theme) for step in steps]
    worst = min(reserved)
    entry: dict[str, Any] = {
        "steps": steps,
        "oklchL": [round(oklch(step)[0], 3) for step in steps],
        "firstVs": {name: round(delta_e(steps[0], colour), 1) for name, colour in surfaces.items()},
        "reservedMin": {"deltaE": worst[0], "token": worst[1], "step": reserved.index(worst) + 1},
        "adjacentMin": round(min(delta_e(steps[i], steps[i + 1]) for i in range(len(steps) - 1)), 1),
    }
    if key in RAMP_MARKERS:
        label, index = RAMP_MARKERS[key]
        entry[label] = {name: round(delta_e(steps[index], colour), 1) for name, colour in surfaces.items()}
    return entry


def ramp_tokens(system: System) -> dict[str, Any]:
    ramps: dict[str, Any] = {}
    for key, ramp in system.data["ramps"].items():
        token = {name: value for name, value in ramp.items() if name not in system.themes and name != "spec"}
        for theme in system.themes:
            token[theme] = _ramp_theme(system, key, _ramp_steps(ramp, theme), theme)
        token["cssVars"] = [f"--{key}-{i + 1}" for i in range(len(token["light"]["steps"]))]
        ramps[key] = token
    return ramps


def _family_contrast(system: System, colour: str, theme: str) -> dict[str, float]:
    return {
        "ground": round(contrast(colour, system.sem("ground", theme)), 2),
        "sunk": round(contrast(colour, system.sem("sunk", theme)), 2),
        "land": round(contrast(colour, system.map_colour("map-land", theme)), 2),
    }


def _family_theme(system: System, palette: list[str], theme: str) -> dict[str, Any]:
    order = system.data["familyOrder"]
    pairs = list(pairwise(palette))
    reserved = min(system.reserved_min(colour, theme) for colour in palette)
    return {
        "colors": dict(zip(order, palette, strict=True)),
        "worstAdjacentCvdDeltaE": min(round(cvd_delta_e(a, b), 1) for a, b in pairs),
        "worstAdjacentNormalDeltaE": min(round(delta_e(a, b), 1) for a, b in pairs),
        "reservedMin": {"deltaE": reserved[0], "token": reserved[1]},
        "contrast": {
            name: _family_contrast(system, colour, theme) for name, colour in zip(order, palette, strict=True)
        },
    }


def family_tokens(system: System) -> dict[str, Any]:
    data = system.data
    notes = data["familyNotes"]
    tokens: dict[str, Any] = {
        "order": data["familyOrder"],
        "labels": data["familyLabel"],
        "other": {
            "label": notes["otherLabel"],
            **{theme: data["familyOther"][theme] for theme in system.themes},
        },
        "cssVars": [f"--fam-{name}" for name in data["familyOrder"]] + ["--fam-other"],
        "rule": notes["rule"],
    }
    for theme in system.themes:
        tokens[theme] = _family_theme(system, data["families"][theme], theme)
    tokens["validation"] = notes["validation"]
    tokens["whyNotMaterialHues"] = notes["whyNotMaterialHues"]
    return tokens


def _map_entry(system: System, name: str, value: str, theme: str) -> dict[str, Any]:
    colour = system.resolve(value, theme)
    entry: dict[str, Any] = {"hex": colour, "ref": value if not value.startswith("#") else None}
    grounds = {surface: system.map_colour(f"map-{surface}", theme) for surface in ("land", "water", "salt")}
    if name in MAP_CONTRAST:
        entry["contrast"] = {
            surface: round(contrast(colour, grounds[surface]), 2) for surface in MAP_CONTRAST[name]
        }
    elif name in MAP_DELTA:
        entry["deltaE"] = {
            surface: round(delta_e(colour, grounds[surface]), 1) for surface in MAP_DELTA[name]
        }
    return entry


def map_tokens(system: System) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    for name, kind, use, *values in system.data["map"]:
        token: dict[str, Any] = {"cssVar": f"--{name}", "class": kind, "use": use}
        for theme, value in zip(system.themes, values, strict=True):
            token[theme] = _map_entry(system, name, value, theme)
        tokens[name] = token
    tokens["map-hillshade"] = system.data["mapHillshade"]
    tokens["rules"] = system.data["mapRules"]
    return tokens
