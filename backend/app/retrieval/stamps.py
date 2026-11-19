from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, String, func, or_, select

__all__ = ["current_embedding_model", "made_by_current_model", "needs_vector"]


def current_embedding_model() -> ColumnElement[str]:
    return select(func.kv_embedding_model(type_=String())).scalar_subquery()


def made_by_current_model(stamp: Any) -> ColumnElement[bool]:
    return stamp == current_embedding_model()


def needs_vector(embedding: Any, stamp: Any) -> ColumnElement[bool]:
    return or_(embedding.is_(None), stamp.is_distinct_from(current_embedding_model()))
