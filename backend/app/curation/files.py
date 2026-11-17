from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.data.craft_master_loader import DATA_DIR

from .check_file import CheckFile
from .checks import CheckContext, content_problems, dossier_problems
from .dossier import Dossier, parse_dossier
from .problems import Problem, schema_problems

__all__ = [
    "CHECK_SUFFIX",
    "CURATION_DIR",
    "INDEX_NAME",
    "DossierResult",
    "check_path",
    "checked_dossier",
    "dossier_paths",
    "read_check_file",
    "stray_problems",
]

CURATION_DIR = DATA_DIR / "curation"
INDEX_NAME = "index.json"
CHECK_SUFFIX = ".check.json"
DOSSIER_SUFFIX = ".json"


@dataclass(frozen=True)
class DossierResult:
    path: Path
    dossier: Dossier | None
    check: CheckFile | None
    problems: tuple[Problem, ...]


def dossier_paths(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob(f"*{DOSSIER_SUFFIX}")
        if path.name != INDEX_NAME and not path.name.endswith(CHECK_SUFFIX)
    )


def check_path(dossier_path: Path, craft_slug: str) -> Path:
    return dossier_path.with_name(f"{craft_slug}{CHECK_SUFFIX}")


def read_check_file(path: Path) -> CheckFile | None:
    if not path.is_file():
        return None
    return CheckFile.model_validate_json(path.read_bytes())


def checked_dossier(path: Path, context: CheckContext) -> DossierResult:
    try:
        dossier = parse_dossier(path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError:
        return DossierResult(path, None, None, (Problem("file", "is not UTF-8 text"),))
    except ValidationError as error:
        return DossierResult(path, None, None, tuple(schema_problems(error)))
    named = f"{dossier.craft_slug}{DOSSIER_SUFFIX}"
    found = (
        []
        if path.name == named
        else [Problem("file", f"the dossier of {dossier.craft_slug} is named {named}")]
    )
    try:
        check = read_check_file(check_path(path, dossier.craft_slug))
    except ValidationError as error:
        unreadable = [
            Problem("check file", f"{problem.where}: {problem.message}") for problem in schema_problems(error)
        ]
        return DossierResult(
            path, dossier, None, tuple(found + content_problems(dossier, context) + unreadable)
        )
    return DossierResult(path, dossier, check, tuple(found + dossier_problems(dossier, context, check)))


def stray_problems(directory: Path) -> list[Problem]:
    dossiers = {path.name for path in dossier_paths(directory)}
    found = []
    for path in sorted(directory.iterdir()):
        if path.name in dossiers or path.name == INDEX_NAME or path.name.startswith("."):
            continue
        if not path.name.endswith(CHECK_SUFFIX):
            found.append(Problem(path.name, "is not a dossier, a check file or the index"))
        elif path.name.removesuffix(CHECK_SUFFIX) + DOSSIER_SUFFIX not in dossiers:
            found.append(Problem(path.name, "is a check file without its dossier"))
    return found
