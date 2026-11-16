from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

__all__ = [
    "FILE_LINE_BUDGET",
    "FUNCTION_LINE_BUDGET",
    "PARAMETER_BUDGET",
    "BudgetFindings",
    "Overrun",
    "measure_budgets",
]

FILE_LINE_BUDGET = 400
FUNCTION_LINE_BUDGET = 40
PARAMETER_BUDGET = 5

_RECEIVER_NAMES = frozenset({"self", "cls"})


@dataclass(frozen=True, order=True)
class Overrun:
    path: str
    line: int
    name: str
    size: int
    budget: int

    def describe(self) -> str:
        return f"{self.path}:{self.line}: {self.name} is {self.size} (budget {self.budget})"


@dataclass(frozen=True)
class BudgetFindings:
    oversized_files: tuple[Overrun, ...]
    long_functions: tuple[Overrun, ...]
    wide_functions: tuple[Overrun, ...]


def measure_budgets(sources: Iterable[tuple[PurePosixPath, str]]) -> BudgetFindings:
    files: list[Overrun] = []
    long: list[Overrun] = []
    wide: list[Overrun] = []
    for path, text in sources:
        line_count = len(text.splitlines())
        if line_count > FILE_LINE_BUDGET:
            files.append(Overrun(str(path), 1, path.name, line_count, FILE_LINE_BUDGET))
        for node in _functions(ast.parse(text, filename=str(path))):
            length = node.end_lineno - node.lineno + 1
            if length > FUNCTION_LINE_BUDGET:
                long.append(Overrun(str(path), node.lineno, node.name, length, FUNCTION_LINE_BUDGET))
            positional = _positional_count(node)
            if positional > PARAMETER_BUDGET:
                wide.append(Overrun(str(path), node.lineno, node.name, positional, PARAMETER_BUDGET))
    return BudgetFindings(tuple(sorted(files)), tuple(sorted(long)), tuple(sorted(wide)))


def _functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _positional_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    names = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args)]
    if names and names[0] in _RECEIVER_NAMES:
        names = names[1:]
    return len(names)
