import uuid
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from app.core.errors import ExternalFailure
from app.services import orphan_concepts, upkeep_archive
from app.services.orphan_concepts import (
    ORPHAN_MIN_AGE,
    ORPHANS_PER_NIGHT,
    OrphanConcept,
    orphaned,
    sweep_orphans,
)
from app.services.upkeep_archive import ARCHIVES_PER_NIGHT, AtRisk, archive_sources

from .fakes import NIGHT, ScriptedArchiver

SAVED = "https://crafts.example.org/a"
OFF_PATTERN = "https://crafts.example.org/b"
REFUSED = "https://crafts.example.org/c"


class Committing:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


async def test_only_a_snapshot_on_the_wayback_pattern_is_recorded_as_the_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limits: list[int] = []
    archived: list[tuple[uuid.UUID, str]] = []
    tried: list[uuid.UUID] = []
    at_risk = [AtRisk(uuid.UUID(int=n), url) for n, url in enumerate((SAVED, OFF_PATTERN, REFUSED), start=1)]

    async def sources_at_risk(session: Any, *, now: Any, limit: int) -> list[AtRisk]:
        limits.append(limit)
        return at_risk[:limit]

    async def record_archive(session: Any, source_id: uuid.UUID, snapshot: str, *, now: Any) -> None:
        archived.append((source_id, snapshot))

    async def record_archive_try(session: Any, source_id: uuid.UUID, *, now: Any) -> None:
        tried.append(source_id)

    monkeypatch.setattr(upkeep_archive, "sources_at_risk", sources_at_risk)
    monkeypatch.setattr(upkeep_archive, "record_archive", record_archive)
    monkeypatch.setattr(upkeep_archive, "record_archive_try", record_archive_try)
    archiver = ScriptedArchiver(
        {
            OFF_PATTERN: "https://archive.example.org/b",
            REFUSED: ExternalFailure("answered 429", kind="rate_limit", status=429),
        }
    )
    report = await archive_sources(Committing(), archiver, now=NIGHT)  # type: ignore[arg-type]
    assert limits == [ARCHIVES_PER_NIGHT] == [10]
    assert archiver.saved == [SAVED, OFF_PATTERN, REFUSED]
    assert archived == [(uuid.UUID(int=1), f"https://web.archive.org/web/20261120003000/{SAVED}")]
    assert tried == [uuid.UUID(int=2), uuid.UUID(int=3)]
    assert report.as_dict() == {"archived": 1, "archiveFailed": 2}


def orphan(n: int) -> OrphanConcept:
    return OrphanConcept(uuid.UUID(int=n), f"Concept {n}", "MATERIAL", None)


async def test_an_orphan_is_reported_one_night_and_removed_only_the_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[list[uuid.UUID]] = []
    audits: list[dict[str, Any]] = []
    limits: list[int] = []

    async def orphans_now(session: Any, *, now: Any, limit: int = ORPHANS_PER_NIGHT) -> list[OrphanConcept]:
        limits.append(limit)
        return [orphan(1), orphan(2)]

    async def reported_before(session: Any) -> set[uuid.UUID]:
        return {uuid.UUID(int=1), uuid.UUID(int=9)}

    async def remove(session: Any, orphans: list[OrphanConcept], *, now: Any) -> int:
        removed.append([found.concept_id for found in orphans])
        return len(orphans)

    async def record(session: Any, **entry: Any) -> None:
        audits.append(entry)

    monkeypatch.setattr(orphan_concepts, "orphan_concepts", orphans_now)
    monkeypatch.setattr(orphan_concepts, "_reported_before", reported_before)
    monkeypatch.setattr(orphan_concepts, "remove_orphan_concepts", remove)
    monkeypatch.setattr(orphan_concepts.audit, "record", record)
    report = await sweep_orphans(Committing(), now=NIGHT)  # type: ignore[arg-type]
    assert limits == [500]
    assert removed == [[uuid.UUID(int=1)]]
    assert audits == [
        {"action": "upkeep.orphans_reported", "detail": {"conceptIds": [str(uuid.UUID(int=2))]}}
    ]
    assert report.as_dict()["orphansRemoved"] == 1
    assert report.as_dict()["orphansReported"] == 1


LINKS = (
    '"Claim"',
    '"ConceptEdge"',
    '"ProcessStage"',
    '"Material"',
    '"KnowledgePieceSubject"',
    '"TermConcept"',
)


def test_the_orphan_rule_asks_every_link_and_spares_curated_and_young_concepts() -> None:
    rule = str(orphaned(NIGHT).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert all(f"NOT (EXISTS (SELECT * \nFROM {table}" in rule for table in LINKS), rule
    assert '"Concept"."originRef" IN (\'live_research\')' in rule
    assert "'2026-11-13 00:30:00+00:00'" in rule
    assert ORPHAN_MIN_AGE.days == 7
