from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from .base import ContractModel, HttpsUrl

__all__ = [
    "BOUNDARY_CAPTION",
    "BOUNDARY_DATASET_CODE",
    "DATASET_CODE_PATTERN",
    "DatasetRef",
    "dataset_codes_problems",
]

DATASET_CODE_PATTERN = r"^[A-Z0-9]+(?:_[A-Z0-9]+)*$"
BOUNDARY_DATASET_CODE = "DR_DISTRICT_SHAPES"
BOUNDARY_CAPTION = (
    "External boundaries of India as depicted by Survey of India. District boundaries are indicative."
)


class DatasetRef(ContractModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1)
    publisher: str | None
    edition: str = Field(min_length=1)
    period: str = Field(min_length=1)
    native_resolution: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    licence_url: HttpsUrl | None
    attribution: str | None
    citation: str | None
    url: HttpsUrl | None


def dataset_codes_problems(owner: str, datasets: Iterable[DatasetRef], needed: Iterable[str]) -> list[str]:
    codes = [dataset.code for dataset in datasets]
    problems = []
    if len(set(codes)) != len(codes):
        problems.append(f"{owner} cites each dataset once")
    missing = [code for code in dict.fromkeys(needed) if code not in codes]
    if missing:
        problems.append(f"{owner} cites the dataset rows it draws: {', '.join(missing)} missing")
    return problems
