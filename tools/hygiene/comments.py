from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

__all__ = ["DIRECTIVE", "CommentViolation", "comment_language", "comment_violations"]

DIRECTIVE = re.compile(r"#\s*(noqa\b|type:\s*ignore\b|pragma:|fmt:\s*(off|on|skip)\b)")
HASH_DIRECTIVE = re.compile(r"#!|#\s*(shellcheck\b|syntax=|yaml-language-server:|-\*-)")
SLASH_DIRECTIVE = re.compile(
    r"eslint-(disable|enable)|@ts-(expect-error|ignore)|///\s*<reference|prettier-ignore"
)
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
LINE_COMMENT = re.compile(r"(?:^|[\s;,{}()])//")
BLOCK_COMMENT = re.compile(r"/\*")
MARKUP_COMMENT = re.compile(r"<!--")
VENDORED = (".claude/skills/security-audit/", "backend/app/data/exports/reveal/")
HASH_NAMES = frozenset({".gitignore", ".gitattributes", ".dockerignore", "Dockerfile"})
LANGUAGES = {
    ".py": "python",
    ".ts": "slash",
    ".tsx": "slash",
    ".js": "slash",
    ".mjs": "slash",
    ".cjs": "slash",
    ".css": "css",
    ".tf": "terraform",
    ".yml": "hash",
    ".yaml": "hash",
    ".sh": "hash",
    ".toml": "hash",
    ".service": "hash",
    ".ps1": "hash",
    ".cfg": "hash",
    ".ini": "hash",
    ".conf": "hash",
    ".example": "hash",
    ".html": "markup",
    ".xml": "markup",
    ".svg": "markup",
}


@dataclass(frozen=True, order=True)
class CommentViolation:
    path: str
    line: int
    text: str

    def describe(self) -> str:
        return f"{self.path}:{self.line}: {self.text}"


def comment_language(path: PurePosixPath) -> str | None:
    if str(path).startswith(VENDORED):
        return None
    if path.name in HASH_NAMES:
        return "hash"
    return LANGUAGES.get(path.suffix)


def comment_violations(sources: Iterable[tuple[PurePosixPath, str]]) -> list[CommentViolation]:
    found: list[CommentViolation] = []
    for path, text in sources:
        found.extend(_violations(path, text))
    return sorted(found)


def _violations(path: PurePosixPath, text: str) -> list[CommentViolation]:
    language = comment_language(path)
    if language == "python":
        return _python_comments(path, text) + _docstrings(path, text)
    if language == "hash":
        return _hash_lines(path, text)
    if language in {"slash", "css"}:
        return _slash_lines(path, text, line_comments=language == "slash")
    if language == "terraform":
        return _hash_lines(path, text) + _slash_lines(path, text, line_comments=True)
    if language == "markup":
        return _marked(path, text, MARKUP_COMMENT)
    return []


def _python_comments(path: PurePosixPath, text: str) -> list[CommentViolation]:
    found = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        if (line == 1 and token.string.startswith("#!")) or DIRECTIVE.match(token.string):
            continue
        found.append(CommentViolation(str(path), line, token.string[:80]))
    return found


def _docstrings(path: PurePosixPath, text: str) -> list[CommentViolation]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    owners = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    nodes = [tree, *(node for node in ast.walk(tree) if isinstance(node, owners))]
    return [
        CommentViolation(str(path), node.body[0].lineno, "docstring")
        for node in nodes
        if ast.get_docstring(node, clean=False) is not None
    ]


def _hash_lines(path: PurePosixPath, text: str) -> list[CommentViolation]:
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        if (number == 1 and stripped.startswith("#!")) or HASH_DIRECTIVE.match(stripped):
            continue
        found.append(CommentViolation(str(path), number, stripped[:80]))
    return found


def _slash_lines(path: PurePosixPath, text: str, *, line_comments: bool) -> list[CommentViolation]:
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if SLASH_DIRECTIVE.search(line):
            continue
        code = STRING_LITERAL.sub('""', line)
        if BLOCK_COMMENT.search(code) or (line_comments and LINE_COMMENT.search(code)):
            found.append(CommentViolation(str(path), number, line.strip()[:80]))
    return found


def _marked(path: PurePosixPath, text: str, marker: re.Pattern[str]) -> list[CommentViolation]:
    return [
        CommentViolation(str(path), number, line.strip()[:80])
        for number, line in enumerate(text.splitlines(), start=1)
        if marker.search(line)
    ]
