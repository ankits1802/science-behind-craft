import uuid
from typing import Any

from app.services.curated_index import IndexPicture

__all__ = ["CLAIM", "picture"]

CLAIM = uuid.UUID("9a1e0000-0000-4000-8000-0000000000c1")


def picture(key: str, *, role: str | None = None, chapter: str = "glance", **extra: Any) -> IndexPicture:
    placement = None if role is None else {"chapter": chapter, "role": role, **extra.pop("placed", {})}
    return IndexPicture.model_validate(
        {
            "key": key,
            "mediaRefId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://example.org/{key}")),
            "caption": f"Picture {key}",
            "stageKey": extra.pop("stage_key", None),
            "claimIds": [str(CLAIM)],
            "placement": placement,
            **extra,
        }
    )
