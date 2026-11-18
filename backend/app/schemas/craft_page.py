from __future__ import annotations

from app.research.base import ContractModel

__all__ = ["PageHiding"]


class PageHiding(ContractModel):
    hidden: bool
