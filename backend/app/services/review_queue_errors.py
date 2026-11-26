from __future__ import annotations

from pydantic import ValidationError

from app.core.errors import AppError

__all__ = ["DecisionConflict", "NotYourQueue", "OwnItem", "UnknownCraft", "UnknownItem", "refusal_of"]


class UnknownItem(AppError):
    pass


class UnknownCraft(AppError):
    pass


class DecisionConflict(AppError):
    pass


class OwnItem(AppError):
    pass


class NotYourQueue(AppError):
    pass


def refusal_of(refused: AppError | ValidationError) -> str:
    if isinstance(refused, ValidationError):
        return "; ".join(str(problem["msg"]) for problem in refused.errors())
    return str(refused) or type(refused).__name__
