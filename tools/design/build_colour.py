from __future__ import annotations

from typing import Any

from design.colour import contrast, delta_e, fmt_oklch
from design.system import System, colour_entry, mix, specimen_hex

__all__ = ["colour_tokens", "plate_tokens", "specimen_tokens"]

PAGE_SURFACES = ("ground", "raised", "sunk")
FILL_SURFACES = {"on-indigo": ("indigo", "indigo-hover"), "on-madder": ("madder",)}
FRAME_EDGE = 3


def _themed_colour(system: System, name: str, theme: str, colour: str) -> dict[str, Any]:
    entry: dict[str, Any] = colour_entry(colour)
    against = FILL_SURFACES.get(name, PAGE_SURFACES)
    entry["contrast"] = {
        surface: round(contrast(colour, system.sem(surface, theme)), 2) for surface in against
    }
    return entry


def colour_tokens(system: System) -> dict[str, Any]:
    color: dict[str, Any] = {}
    for name, kind, role, use, *values in system.data["semantic"]:
        token = {
            "cssVar": f"--c-{name}",
            "alias": f"--{name}",
            "tailwind": name,
            "class": kind,
            "role": role,
            "use": use,
        }
        for theme, colour in zip(system.themes, values, strict=True):
            token[theme] = _themed_colour(system, name, theme, colour)
        color[name] = token
    for fg, bg in system.data["onTextPairs"]:
        pair = {
            theme: round(contrast(system.sem(fg, theme), system.sem(bg, theme)), 2) for theme in system.themes
        }
        color[bg].setdefault("onText", {})[fg] = pair
    info_gap = {
        theme: round(delta_e(system.sem("info", theme), system.sem("indigo", theme)), 1)
        for theme in system.themes
    }
    color["indigo"]["checks"] = {"infoVsIndigoDeltaE": info_gap}
    return color


def _specimen_frame(system: System, colour: str, theme: str) -> dict[str, Any]:
    frame = contrast(colour, system.sem("ink-2", theme))
    mat = contrast(colour, system.sem("raised", theme))
    return {"vsFrame": round(frame, 2), "vsMat": round(mat, 2), "edgeVisible": max(frame, mat) >= FRAME_EDGE}


def _specimen_entry(system: System, row: list[Any]) -> dict[str, Any]:
    name, shows = row[0], row[2]
    colour = specimen_hex(row)
    on_photo = name.startswith("photo")
    entry = {
        "cssVar": f"--{name}",
        "hex": colour,
        "oklch": fmt_oklch(colour),
        "shows": shows,
        "class": "text-on-photo" if on_photo else "specimen",
    }
    if on_photo:
        return entry
    nearest = {theme: system.reserved_min(colour, theme) for theme in system.themes}
    entry["nearestSemantic"] = {
        theme: {"deltaE": gap, "token": token} for theme, (gap, token) in nearest.items()
    }
    entry["frame"] = {theme: _specimen_frame(system, colour, theme) for theme in system.themes}
    return entry


def specimen_tokens(system: System) -> dict[str, Any]:
    tokens = {row[0]: _specimen_entry(system, row) for row in system.data["specimen"]}
    tokens.update(system.data["photoScrims"])
    return tokens


def plate_tokens(system: System) -> dict[str, Any]:
    plates: dict[str, Any] = {}
    for key, label, texture, *values in system.data["plates"]:
        spec = system.data["textures"][texture]
        token = {
            "label": label,
            "texture": texture,
            "cssVar": f"--plate-{key}",
            "inkVar": f"--plate-{key}-ink",
            "textureSpec": spec,
        }
        for theme, (ground, ink) in zip(system.themes, values, strict=True):
            textured = mix(ink, ground, spec["opacity"])
            token[theme] = {
                "ground": ground,
                "ink": ink,
                "contrast": round(contrast(ground, ink), 2),
                "textureDeltaE": round(delta_e(ground, textured), 1),
            }
        plates[key] = token
    plates["rules"] = system.data["plateRules"]
    return plates
