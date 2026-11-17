from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from .citation_export import CitationEntry
from .citation_formats import dataset_access_key
from .citations import AnswerSentence
from .media_refs import MediaRef

__all__ = ["CREDIT_SEPARATOR", "DOI_PREFIX", "References", "marker", "picture_credit", "reference_link"]

CREDIT_SEPARATOR = " · "
DOI_PREFIX = "https://doi.org/"


@dataclass(frozen=True)
class References:
    entries: tuple[CitationEntry, ...]
    numbers: Mapping[str, int] = field(init=False)

    def __post_init__(self) -> None:
        numbers = {
            entry.source_id or dataset_access_key(entry.dataset_code or ""): entry.number
            for entry in self.entries
        }
        if [entry.number for entry in self.entries] != list(range(1, len(self.entries) + 1)):
            raise ValueError("references are numbered 1 to n")
        object.__setattr__(self, "numbers", numbers)

    def sentence_marker(self, sentence: AnswerSentence) -> str:
        return marker(self._number(citation.source_id) for citation in sentence.citations)

    def dataset_marker(self, codes: Iterable[str]) -> str:
        return marker(self._number(dataset_access_key(code)) for code in codes)

    def of_source(self, source_id: str) -> CitationEntry:
        return self.entries[self._number(source_id) - 1]

    def _number(self, key: str) -> int:
        number = self.numbers.get(key)
        if number is None:
            raise ValueError(f"{key} is cited but has no numbered reference")
        return number


def marker(numbers: Iterable[int]) -> str:
    listed = sorted(set(numbers))
    return f"[{', '.join(str(number) for number in listed)}]" if listed else ""


def picture_credit(media: MediaRef) -> str:
    parts: Sequence[str | None] = (media.title, media.author or media.credit, media.licence, media.page_url)
    return CREDIT_SEPARATOR.join(part for part in parts if part)


def reference_link(entry: CitationEntry) -> str | None:
    if entry.csl.doi:
        return f"{DOI_PREFIX}{entry.csl.doi}"
    return entry.csl.url
