from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass

from app.core.errors import InvalidInput

__all__ = ["RRF_K", "VOTING_DEPTH", "FusedItem", "fused_order", "reciprocal_rank_fusion"]

RRF_K = 60
VOTING_DEPTH = 30


@dataclass(frozen=True)
class FusedItem[K: Hashable]:
    key: K
    score: float
    ranks: tuple[int | None, ...]
    voted: float

    @property
    def best_rank(self) -> int:
        return min(rank for rank in self.ranks if rank is not None)


def reciprocal_rank_fusion[K: Hashable](
    rankings: Sequence[Sequence[K]], *, k: int = RRF_K, voting_depth: int = VOTING_DEPTH
) -> list[FusedItem[K]]:
    if k <= 0:
        raise InvalidInput(f"The fusion constant must be positive, not {k}")
    if voting_depth <= 0:
        raise InvalidInput(f"A ranking votes with at least its first item, not {voting_depth}")
    positions = [_positions(index, ranking) for index, ranking in enumerate(rankings)]
    keys = {key for found in positions for key in found}
    fused = [
        _fused(key, tuple(found.get(key) for found in positions), k=k, voting_depth=voting_depth)
        for key in keys
    ]
    return sorted(fused, key=fused_order)


def fused_order[K: Hashable](item: FusedItem[K]) -> tuple[float, float, int, str]:
    return (-item.voted, -item.score, item.best_rank, str(item.key))


def _fused[K: Hashable](key: K, ranks: tuple[int | None, ...], *, k: int, voting_depth: int) -> FusedItem[K]:
    found = [rank for rank in ranks if rank is not None]
    voting = [rank for rank in found if rank <= voting_depth]
    return FusedItem(key=key, score=_summed(found, k=k), ranks=ranks, voted=_summed(voting, k=k))


def _summed(ranks: Iterable[int], *, k: int) -> float:
    return sum((1.0 / (k + rank) for rank in ranks), 0.0)


def _positions[K: Hashable](index: int, ranking: Sequence[K]) -> dict[K, int]:
    found: dict[K, int] = {}
    for rank, key in enumerate(ranking, start=1):
        if key in found:
            raise InvalidInput(f"Ranking {index} lists {key!r} twice")
        found[key] = rank
    return found
