from math import ceil
from typing import Any

from pydantic import BaseModel, ConfigDict

MAX_PAGE_SIZE = 200


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)


def normalize_pagination(page: int, page_size: int) -> tuple[int, int, int]:
    clean_page = max(1, page)
    clean_size = max(1, min(page_size, MAX_PAGE_SIZE))
    return clean_page, clean_size, (clean_page - 1) * clean_size


def page_payload(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }
