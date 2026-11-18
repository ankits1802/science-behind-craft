from __future__ import annotations

import hashlib
import json
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.research.base import ContractModel, HttpsUrl

from .dossier import Dossier
from .fields import CRAFT_SLUG_PATTERN, ClaimId, SourceId
from .problems import Problem
from .vocabulary import QuoteResult, ReadRoute

__all__ = [
    "CHECK_FILE_SCHEMA_VERSION",
    "SHA256_PATTERN",
    "VERIFY_TOOL",
    "CheckFile",
    "QuoteCheckEntry",
    "SourceCheck",
    "check_file_problems",
    "check_file_text",
    "verified_digest",
]

CHECK_FILE_SCHEMA_VERSION = 1
VERIFY_TOOL = "kalavigyan-curation-verify/2"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
SLUG_KEYS = ("craftSlug", "categorySlug")


class SourceCheck(ContractModel):
    source_id: SourceId
    url: HttpsUrl
    route: ReadRoute | None = None
    read_url: str | None = Field(default=None, max_length=4096)
    final_url: str | None = Field(default=None, max_length=4096)
    fetched_at: AwareDatetime
    content_type: str | None = Field(default=None, max_length=100)
    text_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    characters: int | None = Field(default=None, ge=0)
    truncated: bool = False
    problem: str | None = Field(default=None, max_length=2000)

    @property
    def read(self) -> bool:
        return self.text_sha256 is not None and self.problem is None


class QuoteCheckEntry(ContractModel):
    claim_id: ClaimId
    source_id: SourceId
    quote: str = Field(min_length=1)
    result: QuoteResult


class CheckFile(ContractModel):
    schema_version: Literal[1] = CHECK_FILE_SCHEMA_VERSION
    craft_slug: str | None = Field(default=None, pattern=CRAFT_SLUG_PATTERN)
    category_slug: str | None = Field(default=None, pattern=CRAFT_SLUG_PATTERN)
    dossier_version: int = Field(ge=1)
    dossier_digest: str = Field(pattern=SHA256_PATTERN)
    checked_at: AwareDatetime
    tool: str = Field(min_length=1, max_length=100)
    sources: list[SourceCheck]
    quotes: list[QuoteCheckEntry]

    @model_validator(mode="after")
    def _one_slug(self) -> Self:
        if (self.craft_slug is None) == (self.category_slug is None):
            raise ValueError("a check file names a craftSlug or a categorySlug, not both")
        return self

    @property
    def slug(self) -> str:
        return self.category_slug or self.craft_slug or ""


def check_file_text(check: CheckFile) -> str:
    plain = check.model_dump(mode="json", by_alias=True)
    for key in SLUG_KEYS:
        if plain[key] is None:
            del plain[key]
    return json.dumps(plain, indent=2, ensure_ascii=False) + "\n"


def verified_digest(dossier: Dossier) -> str:
    material = {
        SLUG_KEYS[dossier.category_slug is not None]: dossier.slug,
        "sources": [[source.id, source.url, source.archived_url] for source in dossier.sources],
        "quotes": [
            [claim.id, quote.source_id, quote.quote] for claim in dossier.claims for quote in claim.quotes
        ],
    }
    text = json.dumps(material, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_file_problems(dossier: Dossier, check: CheckFile | None) -> list[Problem]:
    if check is None:
        return [Problem("check file", f"{dossier.slug}.check.json is missing; run verify")]
    stale = _staleness(dossier, check)
    if stale:
        return [Problem("check file", f"{stale}; run verify again")]
    read = {entry.source_id: entry for entry in check.sources}
    found = [
        Problem(
            source.id, f"could not be read when verified ({read[source.id].problem}); drop it with its claims"
        )
        for source in dossier.sources
        if source.id in read and not read[source.id].read
    ]
    passed = {
        (entry.claim_id, entry.source_id, entry.quote) for entry in check.quotes if entry.result == "PASS"
    }
    for claim in dossier.claims:
        for index, quote in enumerate(claim.quotes):
            if (claim.id, quote.source_id, quote.quote) not in passed:
                found.append(
                    Problem(
                        f"{claim.id}.quotes.{index}",
                        f"did not pass verify against {quote.source_id}; drop the quote",
                    )
                )
    return found


def _staleness(dossier: Dossier, check: CheckFile) -> str | None:
    if (check.craft_slug, check.category_slug) != (dossier.craft_slug, dossier.category_slug):
        return f"the check file is for {check.slug}"
    if check.tool != VERIFY_TOOL:
        return f"the check file was made by {check.tool}, not {VERIFY_TOOL}"
    if check.dossier_digest != verified_digest(dossier):
        return "the dossier's sources or quotes changed after it was verified"
    if check.checked_at < dossier.curated_at:
        return "the check file is older than the dossier's curatedAt"
    if {entry.source_id for entry in check.sources} != {source.id for source in dossier.sources}:
        return "the check file does not cover every source"
    return None
