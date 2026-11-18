from __future__ import annotations

from design.colour import delinear, delta_e, hex_to_rgb, linear, rgb_to_hex

__all__ = ["cvd_delta_e", "simulate"]

MACHADO_SEVERITY_ONE = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}


def simulate(colour: str, kind: str) -> str:
    red, green, blue = (linear(x) for x in hex_to_rgb(colour))
    matrix = MACHADO_SEVERITY_ONE[kind]
    seen = [max(0, min(1, row[0] * red + row[1] * green + row[2] * blue)) for row in matrix]
    return rgb_to_hex(*(delinear(x) for x in seen))


def cvd_delta_e(first: str, second: str) -> float:
    return min(
        delta_e(simulate(first, "protan"), simulate(second, "protan")),
        delta_e(simulate(first, "deutan"), simulate(second, "deutan")),
    )
