from __future__ import annotations

from app.core.errors import InvalidInput
from app.geo.records import DatasetRecord
from app.schemas.region import RegionDataset

__all__ = ["region_dataset", "value_grid"]


def region_dataset(dataset: DatasetRecord) -> RegionDataset:
    return RegionDataset(
        code=dataset.code,
        title=dataset.title,
        publisher=dataset.publisher,
        edition=dataset.edition,
        period=dataset.period,
        native_resolution=dataset.native_resolution,
        licence=dataset.licence,
        licence_url=dataset.licence_url,
        attribution=dataset.attribution,
        citation=dataset.citation,
        url=dataset.url,
    )


def value_grid(resolution: str | None, dataset: DatasetRecord) -> str:
    grid = resolution or dataset.native_resolution
    if not grid:
        raise InvalidInput(f"{dataset.code} names no grid for a stored value")
    return grid
