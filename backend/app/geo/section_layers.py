from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from app.geo.layers import MAP_LAYERS
from app.research.blocks_place import MapLayerBlock
from app.schemas.region import MapLayer

__all__ = [
    "LAYER_SUBJECTS",
    "SECTION_LAYER_FACETS",
    "STORY_LAYER_FACETS",
    "map_layer_block",
    "section_layer_order",
]

SECTION_LAYER_FACETS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"GEOLOGY": ("SOIL", "GEOLOGY", "TERRAIN"), "CLIMATE": ("CLIMATE",)}
)
STORY_LAYER_FACETS = frozenset({"WATER", "CLIMATE", "SOIL", "GEOLOGY", "TERRAIN"})
LAYER_SUBJECTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "soil-ph-0-5cm": ("ph", "acidic", "acidity", "alkaline", "alkalinity"),
        "soil-organic-carbon-0-5cm": ("organic carbon", "organic matter", "humus"),
        "clay-0-5cm": ("clay", "clays"),
        "sand-0-5cm": ("sand", "sandy"),
        "cation-exchange-0-5cm": ("cation exchange",),
        "annual-mean-temperature": ("temperature", "temperatures"),
        "warmest-month-maximum": ("heat", "hot", "summer", "summers"),
        "coldest-month-minimum": ("cold", "winter", "winters", "frost"),
        "annual-precipitation": ("rain", "rains", "rainfall", "precipitation", "drought", "droughts"),
        "monsoon-share": ("monsoon", "monsoons"),
        "elevation": ("elevation", "altitude", "hill", "hills", "mountain", "mountains"),
        "slope": ("slope", "slopes"),
        "mineral-sites": ("mineral", "minerals", "ore", "ores", "mine", "mines", "mining"),
    }
)


def section_layer_order(discipline: str, texts: Sequence[str]) -> list[str]:
    facets = SECTION_LAYER_FACETS.get(discipline, ())
    candidates = [spec.id for spec in MAP_LAYERS if spec.facet in facets]
    folded = [text.casefold() for text in texts]
    named = {
        layer: position
        for layer in candidates
        if (position := _first_named(folded, LAYER_SUBJECTS.get(layer, ()))) is not None
    }
    return sorted(candidates, key=lambda layer: (named.get(layer, len(folded)), candidates.index(layer)))


def map_layer_block(layer: MapLayer, highlighted: Sequence[int], *, block_id: str) -> MapLayerBlock:
    return MapLayerBlock(
        id=block_id,
        kind="map_layer",
        version=1,
        reuse=None,
        layer=layer.layer.id,
        layer_version=layer.version,
        title=layer.layer.title,
        datasets=[layer.dataset, layer.boundary.dataset],
        highlighted=list(highlighted),
        boundary_caption=layer.boundary.caption,
    )


def _first_named(texts: Sequence[str], words: Sequence[str]) -> int | None:
    patterns = [re.compile(rf"\b{re.escape(word)}\b") for word in words]
    return next(
        (position for position, text in enumerate(texts) if any(p.search(text) for p in patterns)), None
    )
