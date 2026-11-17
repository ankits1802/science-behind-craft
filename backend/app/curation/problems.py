from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import ValidationError

__all__ = ["Problem", "schema_problems"]


@dataclass(frozen=True)
class Problem:
    where: str
    message: str

    def line(self, label: str) -> str:
        return f"{label}: {self.where}: {self.message}"


def schema_problems(error: ValidationError) -> list[Problem]:
    return [Problem(_location(entry["loc"]), entry["msg"]) for entry in error.errors(include_url=False)]


def _location(parts: Iterable[int | str]) -> str:
    return ".".join(str(part) for part in parts) or "dossier"
