from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.core.errors import ExternalFailure
from app.models.crafts import EMBEDDING_DIMENSIONS

__all__ = ["EMBEDDING_SERVICE", "TextEmbedder", "checked_vectors"]

EMBEDDING_SERVICE = "embeddings"


class TextEmbedder(Protocol):
    async def __call__(self, texts: list[str]) -> list[list[float]]: ...


def checked_vectors(vectors: Sequence[Sequence[float]] | None, *, expected: int) -> list[list[float]]:
    found = list(vectors or [])
    if len(found) != expected:
        raise ExternalFailure(
            f"The embedding route returned {len(found)} vectors for {expected} texts",
            service=EMBEDDING_SERVICE,
        )
    for vector in found:
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ExternalFailure(
                f"The embedding route returned {len(vector)} dimensions, not {EMBEDDING_DIMENSIONS}",
                service=EMBEDDING_SERVICE,
            )
    return [list(vector) for vector in found]
