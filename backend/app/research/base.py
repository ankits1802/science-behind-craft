from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

__all__ = [
    "PARTIAL_DATE_PATTERN",
    "URL_MAX_CHARS",
    "ContractModel",
    "HttpsUrl",
    "PartialDate",
    "absent",
    "https_url",
]

URL_MAX_CHARS = 2048
PARTIAL_DATE_PATTERN = r"^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$"


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


def absent(value: object) -> bool:
    return value is None


def https_url(value: str) -> str:
    if not value.startswith("https://") or len(value) <= len("https://"):
        raise ValueError("Only https URLs are allowed")
    if len(value) > URL_MAX_CHARS:
        raise ValueError(f"A URL is at most {URL_MAX_CHARS} characters")
    if any(ch.isspace() for ch in value):
        raise ValueError("A URL has no whitespace")
    return value


def partial_date(value: str) -> str:
    if not re.fullmatch(PARTIAL_DATE_PATTERN, value):
        raise ValueError("Use YYYY, YYYY-MM or YYYY-MM-DD")
    return value


HttpsUrl = Annotated[str, AfterValidator(https_url)]
PartialDate = Annotated[str, AfterValidator(partial_date)]
