from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

from app.core.errors import InvalidInput

__all__ = ["RRF_K", "FusedItem", "reciprocal_rank_fusion"]

RRF_K = 60


@dataclass(frozen=True)
class FusedItem[K: Hashable]:
    key: K
    score: float
    ranks: tuple[int | None, ...]

    @property
    def best_rank(self) -> int:
        return min(rank for rank in self.ranks if rank is not None)


def reciprocal_rank_fusion[K: Hashable](
    rankings: Sequence[Sequence[K]], *, k: int = RRF_K
) -> list[FusedItem[K]]:
    if k <= 0:
        raise InvalidInput(f"The fusion constant must be positive, not {k}")
    positions = [_positions(index, ranking) for index, ranking in enumerate(rankings)]
    keys = {key for found in positions for key in found}
    fused = [
        FusedItem(
            key=key,
            score=sum(1.0 / (k + found[key]) for found in positions if key in found),
            ranks=tuple(found.get(key) for found in positions),
        )
        for key in keys
    ]
    return sorted(fused, key=lambda item: (-item.score, item.best_rank, str(item.key)))


def _positions[K: Hashable](index: int, ranking: Sequence[K]) -> dict[K, int]:
    found: dict[K, int] = {}
    for rank, key in enumerate(ranking, start=1):
        if key in found:
            raise InvalidInput(f"Ranking {index} lists {key!r} twice")
        found[key] = rank
    return found
