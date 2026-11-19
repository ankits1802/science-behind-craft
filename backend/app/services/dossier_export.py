from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.curation.check_file import check_file_problems
from app.curation.checks import CheckContext, default_context
from app.curation.dossier import parse_dossier
from app.curation.dossier_text import dossier_text
from app.curation.files import CATEGORIES_DIR_NAME, CURATION_DIR, check_path, read_check_file
from app.models import Craft, CraftCategory, CuratedCategory, CuratedCraft

from .curation_keys import CURATED_STATUS
from .dossier_diff import dossier_changes
from .dossier_export_assembly import ExportedDossier, exported_dossier
from .dossier_export_records import GitDossier, StoredCuration
from .dossier_export_store import stored_category, stored_craft

__all__ = [
    "CHANGED",
    "CURRENT",
    "DOSSIER_DIR",
    "LAYOUT",
    "MISSING",
    "NEW",
    "SAME",
    "STALE",
    "DossierExport",
    "ExportRun",
    "curated_slugs",
    "dossier_file",
    "export_dossier",
    "export_dossiers",
    "git_dossier",
    "stored_export",
]

DOSSIER_DIR = CURATION_DIR
SAME = "SAME"
LAYOUT = "LAYOUT"
CHANGED = "CHANGED"
NEW = "NEW"
CURRENT = "CURRENT"
STALE = "STALE"
MISSING = "MISSING"


@dataclass(frozen=True)
class DossierExport:
    file: str
    slug: str
    version: int
    text: str
    status: str
    check: str
    changes: tuple[str, ...]
    exported: ExportedDossier
    reviewed: tuple[str, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "slug": self.slug,
            "version": self.version,
            "status": self.status,
            "checkFile": self.check,
            "changes": list(self.changes),
            "keptFromGit": list(self.exported.carried),
            "quotesFailingRecheck": self.exported.failed_quotes,
            "reviewed": list(self.reviewed),
        }


@dataclass(frozen=True)
class ExportRun:
    exports: tuple[DossierExport, ...]
    refused: tuple[tuple[str, str], ...]

    def summary(self) -> dict[str, Any]:
        return {
            "exported": len(self.exports),
            "changed": sum(1 for found in self.exports if found.status in (CHANGED, NEW)),
            "refused": [{"slug": slug, "problem": problem} for slug, problem in self.refused],
            "dossiers": [found.summary() for found in self.exports],
        }


async def curated_slugs(session: AsyncSession) -> tuple[list[str], list[str]]:
    crafts = await session.scalars(
        select(Craft.slug).where(Craft.id.in_(select(CuratedCraft.craftId))).order_by(Craft.slug)
    )
    categories = await session.scalars(
        select(CraftCategory.slug)
        .where(CraftCategory.id.in_(select(CuratedCategory.categoryId)))
        .order_by(CraftCategory.slug)
    )
    return list(crafts.all()), list(categories.all())


def dossier_file(slug: str, *, category: bool) -> str:
    return f"{CATEGORIES_DIR_NAME}/{slug}.json" if category else f"{slug}.json"


def git_dossier(directory: Path, slug: str, *, category: bool) -> GitDossier | None:
    file = dossier_file(slug, category=category)
    path = directory / file
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    try:
        dossier = parse_dossier(text)
    except ValidationError as error:
        raise InvalidInput(
            f"{file} in git is not a valid dossier; fix it with tools/curation/check.py"
        ) from error
    try:
        check = read_check_file(check_path(path, slug))
    except ValidationError:
        check = None
    return GitDossier(file=file, text=text, dossier=dossier, check=check)


async def export_dossier(
    session: AsyncSession, slug: str, *, directory: Path = CURATION_DIR, context: CheckContext | None = None
) -> DossierExport:
    category = await session.scalar(select(Craft.id).where(Craft.slug == slug)) is None
    if category:
        stored = await stored_category(session, slug)
    else:
        stored = await stored_craft(session, slug, context or default_context())
    return stored_export(stored, git_dossier(directory, slug, category=category))


def stored_export(stored: StoredCuration, git: GitDossier | None) -> DossierExport:
    exported = exported_dossier(stored, git.dossier if git else None)
    text = dossier_text(exported.dossier, like=git.text if git else None)
    changes = dossier_changes(exported.dossier, git.dossier if git else None)
    category = exported.dossier.category_slug is not None
    return DossierExport(
        file=git.file if git else dossier_file(stored.slug, category=category),
        slug=stored.slug,
        version=exported.dossier.version,
        text=text,
        status=_status(git, text, changes),
        check=_check(git, exported),
        changes=changes,
        exported=exported,
        reviewed=_reviewed(stored),
    )


async def export_dossiers(
    session: AsyncSession,
    slugs: list[str],
    *,
    directory: Path = CURATION_DIR,
    context: CheckContext | None = None,
) -> ExportRun:
    checking = context or default_context()
    if not slugs:
        crafts, categories = await curated_slugs(session)
        slugs = [*crafts, *categories]
    exports: list[DossierExport] = []
    refused: list[tuple[str, str]] = []
    for slug in slugs:
        try:
            exports.append(await export_dossier(session, slug, directory=directory, context=checking))
        except InvalidInput as error:
            refused.append((slug, str(error)))
    return ExportRun(exports=tuple(exports), refused=tuple(refused))


def _status(git: GitDossier | None, text: str, changes: tuple[str, ...]) -> str:
    if git is None:
        return NEW
    if changes:
        return CHANGED
    return SAME if git.text == text else LAYOUT


def _check(git: GitDossier | None, exported: ExportedDossier) -> str:
    if git is None or git.check is None:
        return MISSING
    return STALE if check_file_problems(exported.dossier, git.check) else CURRENT


def _reviewed(stored: StoredCuration) -> tuple[str, ...]:
    return tuple(
        f"{stored.markers[claim_id]['key']}: {row['status']}"
        for claim_id, row in stored.claims.items()
        if row["status"] != CURATED_STATUS and claim_id in stored.markers
    )
