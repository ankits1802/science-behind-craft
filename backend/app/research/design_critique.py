from __future__ import annotations

from pydantic import Field

from .base import ContractModel

__all__ = [
    "CHAPTER_CHARS",
    "NOTES_MAX",
    "NOTE_CHARS",
    "VERDICT_CHARS",
    "DesignCritique",
    "DesignNote",
    "note_line",
]

NOTES_MAX = 24
VERDICT_CHARS = 400
NOTE_CHARS = 300
CHAPTER_CHARS = 60


class DesignNote(ContractModel):
    chapter: str = Field(min_length=1, max_length=CHAPTER_CHARS)
    where: str = Field(min_length=1, max_length=NOTE_CHARS + 1)
    problem: str = Field(min_length=1, max_length=NOTE_CHARS + 1)
    fix: str = Field(min_length=1, max_length=NOTE_CHARS + 1)


class DesignCritique(ContractModel):
    verdict: str = Field(min_length=1, max_length=VERDICT_CHARS)
    notes: list[DesignNote] = Field(default_factory=list, max_length=NOTES_MAX)


def note_line(note: DesignNote) -> str:
    return f"{note.chapter}, {note.where}: {note.problem} {note.fix}"
