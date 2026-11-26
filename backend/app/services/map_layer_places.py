from __future__ import annotations

from app.data.map_layers import held_river_names, held_shapes
from app.research.component_specs_map_parts import MapParts

__all__ = ["held_map_problems"]


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
    rivers = held_river_names()
    shown = ", ".join(sorted(rivers))
    problems += [
        f"the site's rivers name no river {name!r}: name one of {shown}"
        for name in (parts.emphasis.rivers if parts.emphasis else [])
        if name not in rivers
    ]
    return problems
