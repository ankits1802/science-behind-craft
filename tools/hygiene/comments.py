from __future__ import annotations

import io
import re
import tokenize
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

__all__ = ["DIRECTIVE", "CommentViolation", "comment_violations"]

DIRECTIVE = re.compile(r"#\s*(noqa\b|type:\s*ignore\b|pragma:|fmt:\s*(off|on|skip)\b)")


@dataclass(frozen=True, order=True)
class CommentViolation:
    path: str
    line: int
    text: str

    def describe(self) -> str:
        return f"{self.path}:{self.line}: {self.text}"


def comment_violations(sources: Iterable[tuple[PurePosixPath, str]]) -> list[CommentViolation]:
    found: list[CommentViolation] = []
    for path, text in sources:
        found.extend(_comments_in(path, text))
    return sorted(found)


def _comments_in(path: PurePosixPath, text: str) -> list[CommentViolation]:
    found = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        if (line == 1 and token.string.startswith("#!")) or DIRECTIVE.match(token.string):
            continue
        found.append(CommentViolation(str(path), line, token.string[:80]))
    return found
