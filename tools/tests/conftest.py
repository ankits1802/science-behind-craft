from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

RepoBuilder = Callable[[Mapping[str, bytes | str]], Path]


def write_tree(root: Path, files: Mapping[str, bytes | str]) -> None:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        target.write_bytes(data)


def function_source(name: str, total_lines: int, *, parameters: str = "") -> str:
    assignments = "".join(f"    value_{index} = {index}\n" for index in range(total_lines - 2))
    return f"def {name}({parameters}):\n{assignments}    return None\n"


@pytest.fixture
def make_repo(tmp_path: Path) -> RepoBuilder:
    def build(files: Mapping[str, bytes | str]) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        write_tree(root, files)
        return root

    return build
