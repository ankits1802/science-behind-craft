from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.data.kind_fixture_files import kind_fixtures

from .drawing_themes import themed_spec

__all__ = ["PLACED_KEY", "placed_fixture_spec", "served_kind_fixtures"]

KIND_KEY = "kind"
SPEC_KEY = "spec"
PLACED_KEY = "placed"
PLACES_KEY = "places"
FOUND_KEY = "found"


def served_kind_fixtures() -> list[dict[str, Any]]:
    return [_served(fixture) for fixture in kind_fixtures()]


def placed_fixture_spec(spec: Mapping[str, Any], placed: Mapping[str, Any] | None) -> dict[str, Any]:
    if placed is None:
        return dict(spec)
    places = [
        {**place, FOUND_KEY: found} for place, found in zip(spec[PLACES_KEY], placed[PLACES_KEY], strict=True)
    ]
    return {**spec, **placed, PLACES_KEY: places}


def _served(fixture: Mapping[str, Any]) -> dict[str, Any]:
    spec = placed_fixture_spec(fixture[SPEC_KEY], fixture.get(PLACED_KEY))
    served = {key: value for key, value in fixture.items() if key != PLACED_KEY}
    return {**served, SPEC_KEY: themed_spec(fixture[KIND_KEY], spec)}
