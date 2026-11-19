from __future__ import annotations

from app.core.errors import AppError

__all__ = ["DecisionConflict", "NotYourQueue", "OwnItem", "UnknownCraft", "UnknownItem"]


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
