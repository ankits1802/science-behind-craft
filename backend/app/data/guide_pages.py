from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CONTINUED", "PAGE_BYTES", "PagedText", "guide_title", "paged"]

PAGE_BYTES = 6000
WIDEST_CHARACTER_BYTES = 4
SECTION = "## "
TITLE = "# "
FENCE = "```"
CONTINUED = "{title} (continued)"


@dataclass(frozen=True)
class PagedText:
    body: str
    sections: tuple[str, ...]


@dataclass(frozen=True)
class _Piece:
    section: str
    first: bool
    text: str

    @property
    def size(self) -> int:
        return _bytes(self.text)


def paged(text: str, *, size: int = PAGE_BYTES) -> tuple[PagedText, ...]:
    if size < WIDEST_CHARACTER_BYTES:
        raise ValueError(f"a guide page holds at least {WIDEST_CHARACTER_BYTES} bytes, not {size}")
    pieces = [piece for title, part in _sections(text) for piece in _pieces(title, part, size)]
    return tuple(
        PagedText(body="".join(piece.text for piece in page), sections=_titles(page))
        for page in _packed(pieces, size)
    )


def guide_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith(SECTION):
            return ""
        if line.startswith(TITLE):
            return line[len(TITLE) :].strip()
    return ""


def _bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def _fence(line: str) -> bool:
    return line.lstrip().startswith(FENCE)


def _sections(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, list[str]]] = [(guide_title(text), [])]
    fenced = False
    for line in text.splitlines(keepends=True):
        if not fenced and line.startswith(SECTION):
            found.append((line[len(SECTION) :].strip(), []))
        fenced = fenced != _fence(line)
        found[-1][1].append(line)
    return [(title, "".join(lines)) for title, lines in found if lines]


def _pieces(title: str, text: str, size: int) -> list[_Piece]:
    if _bytes(text) <= size:
        return [_Piece(title, True, text)]
    parts = [part for paragraph in _paragraphs(text) for part in _fitted(paragraph, size)]
    return [_Piece(title, index == 0, part) for index, part in enumerate(parts)]


def _paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    fenced = False
    for line in text.splitlines(keepends=True):
        current.append(line)
        fenced = fenced != _fence(line)
        if not fenced and not line.strip():
            paragraphs.append("".join(current))
            current = []
    if current:
        paragraphs.append("".join(current))
    return paragraphs


def _fitted(paragraph: str, size: int) -> list[str]:
    if _bytes(paragraph) <= size:
        return [paragraph]
    return [chunk for line in paragraph.splitlines(keepends=True) for chunk in _cut(line, size)]


def _cut(line: str, size: int) -> list[str]:
    chunks: list[str] = []
    current, used = "", 0
    for character in line:
        width = _bytes(character)
        if current and used + width > size:
            chunks.append(current)
            current, used = "", 0
        current, used = current + character, used + width
    return [*chunks, current] if current else chunks


def _packed(pieces: list[_Piece], size: int) -> list[list[_Piece]]:
    pages: list[list[_Piece]] = []
    used = 0
    for piece in pieces:
        if pages and used + piece.size <= size:
            pages[-1].append(piece)
            used += piece.size
            continue
        pages.append([piece])
        used = piece.size
    return pages


def _titles(page: list[_Piece]) -> tuple[str, ...]:
    titles: list[str] = []
    for index, piece in enumerate(page):
        if not piece.section:
            continue
        if piece.first:
            titles.append(piece.section)
        elif index == 0:
            titles.append(CONTINUED.format(title=piece.section))
    return tuple(titles)
