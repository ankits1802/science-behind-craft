from collections.abc import Callable
from typing import Any

from fastapi import FastAPI

from app.core.deps import get_current_user, get_optional_user

__all__ = ["sign_in_as"]


def sign_in_as(app: FastAPI, reader: Callable[..., Any]) -> None:
    app.dependency_overrides[get_current_user] = reader
    app.dependency_overrides[get_optional_user] = reader
