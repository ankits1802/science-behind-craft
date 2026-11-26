from __future__ import annotations

from collections.abc import Sequence

from app.data.map_layers import held_dam_names, held_river_names, held_shapes
from app.research.component_specs_map_parts import MapParts

__all__ = ["DAM_UNHELD", "RIVER_UNHELD", "held_map_problems", "held_water_problems"]

RIVER_UNHELD = (
    "the site's rivers name no river {name!r}: name it as Natural Earth or OpenStreetMap names it, or by the name "
    "the site's river register gives a river it matches to those by name and district"
)
DAM_UNHELD = "the site's dams name no dam {name!r}: name it as OpenStreetMap does, by the dam's or its reservoir's name"


def held_map_problems(parts: MapParts) -> list[str]:
    held = held_shapes()
    named = [
        *([parts.frame.district] if parts.frame and parts.frame.district is not None else []),
        *(value.district for value in (parts.districts.values if parts.districts else [])),
    ]
    problems = [
        f"the site holds no shape for the district with LGD code {code}"
        for code in named
        if code not in held.districts
    ]
    if parts.frame and parts.frame.state is not None and parts.frame.state not in held.states:
        problems.append(f"the site holds no shape for the state with LGD code {parts.frame.state}")
    if parts.emphasis:
        problems += held_water_problems(parts.emphasis.rivers, parts.emphasis.dams)
    return problems


def held_water_problems(rivers: Sequence[str], dams: Sequence[str]) -> list[str]:
    held_rivers, held_dams = held_river_names(), held_dam_names()
    return [
        *(RIVER_UNHELD.format(name=name) for name in rivers if name not in held_rivers),
        *(DAM_UNHELD.format(name=name) for name in dams if name not in held_dams),
    ]
