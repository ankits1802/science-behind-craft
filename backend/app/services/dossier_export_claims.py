from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import MappingProxyType

from app.core.errors import InvalidInput
from app.curation.dossier import Dossier
from app.curation.entities import Place
from app.curation.fields import SUBJECT_KINDS, id_kind
from app.curation.parts import CitedQuote, Claim, Source, Subject

from .curation_keys import CURATION_ACTOR, HYPOTHESIS_LEVEL, craft_concept_key
from .dossier_export_records import Row, StoredCuration, guided, id_number

__all__ = ["ExportedEvidence", "PlaceChoices", "claim_keys", "exported_evidence"]

CRAFT_SUBJECT = "CRAFT"
PLACE_SUBJECT = "PLACE"
CRAFT_CONCEPT_PREFIX = craft_concept_key("")
PASSED = "PASS"
SUBJECT_TYPES: Mapping[str, str] = MappingProxyType(
    {kind: subject for subject, kind in SUBJECT_KINDS.items() if subject != PLACE_SUBJECT}
)
DOI_SOURCE_NOTE = "cited through the stored source with its DOI, so it is kept as the dossier in git gives it"

PlaceChoices = Mapping[uuid.UUID, Sequence[Place]]


@dataclass(frozen=True)
class ExportedEvidence:
    sources: list[Source]
    claims: list[Claim]
    carried: list[str]
    failed_quotes: int


@dataclass(frozen=True)
class _Claiming:
    stored: StoredCuration
    keys: Mapping[uuid.UUID, str]
    source_keys: Mapping[uuid.UUID, str]
    quotes: Mapping[uuid.UUID, list[Row]]
    places: PlaceChoices
    earlier: Mapping[str, Claim]


def claim_keys(stored: StoredCuration) -> dict[uuid.UUID, str]:
    unmarked = [str(claim_id) for claim_id in stored.claims if claim_id not in stored.markers]
    if unmarked:
        raise InvalidInput(f"claims of {stored.slug} carry no curated key: {', '.join(unmarked)}")
    return {claim_id: str(stored.markers[claim_id]["key"]) for claim_id in stored.claims}


def exported_evidence(
    stored: StoredCuration, previous: Dossier | None, places: PlaceChoices
) -> ExportedEvidence:
    keys = claim_keys(stored)
    curated = [row for row in stored.quotes if row["foundBy"] == CURATION_ACTOR and row["claimId"] in keys]
    source_keys = _source_keys(stored, curated, previous)
    quotes: dict[uuid.UUID, list[Row]] = defaultdict(list)
    for row in curated:
        quotes[row["claimId"]].append(row)
    claiming = _Claiming(
        stored, keys, source_keys, quotes, places, {c.id: c for c in previous.claims} if previous else {}
    )
    claims = [_claim(claiming, claim_id) for claim_id in _claim_order(stored, keys, previous)]
    sources, carried = _sources(stored, source_keys, previous)
    failed = sum(1 for row in curated if row["quoteCheck"] != PASSED)
    return ExportedEvidence(sources=sources, claims=claims, carried=carried, failed_quotes=failed)


def _claim_order(
    stored: StoredCuration, keys: Mapping[uuid.UUID, str], previous: Dossier | None
) -> list[uuid.UUID]:
    stored_order = [keys[claim_id] for claim_id in stored.claim_order if claim_id in keys]
    earlier = [claim.id for claim in previous.claims] if previous else []
    return guided(stored.claims, keys.__getitem__, [stored_order, earlier], lambda c: id_number(keys[c]))


def _claim(claiming: _Claiming, claim_id: uuid.UUID) -> Claim:
    row = claiming.stored.claims[claim_id]
    key = claiming.keys[claim_id]
    earlier = claiming.earlier.get(key)
    return Claim(
        id=key,
        discipline=row["field"] or claiming.stored.markers[claim_id]["discipline"],
        subject=_subject(claiming, row["subjectId"], key, earlier),
        text=row["text"],
        quotes=_quotes(claiming.quotes.get(claim_id, []), claiming.source_keys, earlier),
        hypothesis=row["evidenceLevel"] == HYPOTHESIS_LEVEL,
        sensitivity=row["sensitivity"],
    )


def _quotes(
    rows: Sequence[Row], source_keys: Mapping[uuid.UUID, str], earlier: Claim | None
) -> list[CitedQuote]:
    cited = [
        CitedQuote(source_id=source_keys[row["sourceId"]], locator=row["locator"], quote=row["quote"])
        for row in rows
    ]
    guide = [(quote.source_id, quote.quote) for quote in earlier.quotes] if earlier else []
    return guided(
        cited, lambda q: (q.source_id, q.quote), [guide], lambda q: (id_number(q.source_id), q.quote)
    )


def _subject(claiming: _Claiming, subject_id: uuid.UUID, key: str, earlier: Claim | None) -> Subject:
    if subject_id in claiming.places:
        return Subject(type=PLACE_SUBJECT, ref=_place_ref(claiming.places[subject_id], key, earlier))
    slug = claiming.stored.slug
    concept = _concept_key(claiming.stored.subjects.get(subject_id), slug)
    if concept is not None and concept.startswith(CRAFT_CONCEPT_PREFIX):
        return Subject(type=CRAFT_SUBJECT)
    subject_type = SUBJECT_TYPES.get(id_kind(concept) or "") if concept else None
    if subject_type is None:
        raise InvalidInput(f"claim {key} of {slug} is about a concept that is not a part of its dossier")
    return Subject(type=subject_type, ref=concept)


def _concept_key(origin: str | None, slug: str) -> str | None:
    prefix = f"curation:{slug}:"
    return origin.removeprefix(prefix) if origin and origin.startswith(prefix) else None


def _place_ref(choices: Sequence[Place], key: str, earlier: Claim | None) -> str:
    ids = [place.id for place in choices]
    if earlier is not None and earlier.subject.ref in ids:
        return str(earlier.subject.ref)
    return next((place.id for place in choices if key in place.claim_ids), ids[0])


def _source_keys(
    stored: StoredCuration, quotes: Sequence[Row], previous: Dossier | None
) -> dict[uuid.UUID, str]:
    by_doi = {source.doi: source.id for source in previous.sources if source.doi} if previous else {}
    keys: dict[uuid.UUID, str] = {}
    for source_id in dict.fromkeys(row["sourceId"] for row in quotes):
        row = stored.sources.get(source_id)
        found = _own_key(row, stored.slug) or (by_doi.get(row["doi"]) if row else None)
        if found is None:
            raise InvalidInput(
                f"a quote of {stored.slug} cites source {source_id}, which is neither the dossier's own "
                "nor one the dossier in git names by its DOI"
            )
        keys[source_id] = found
    return keys


def _own_key(row: Row | None, slug: str) -> str | None:
    marker = str((row["externalIds"] or {}).get("curation") or "") if row else ""
    owner, _, key = marker.rpartition(":")
    return key if owner == slug and key else None


def _sources(
    stored: StoredCuration, source_keys: Mapping[uuid.UUID, str], previous: Dossier | None
) -> tuple[list[Source], list[str]]:
    earlier = {source.id: source for source in previous.sources} if previous else {}
    chosen: dict[str, Source] = {}
    carried: list[str] = []
    for source_id, key in source_keys.items():
        row = stored.sources.get(source_id)
        if key in chosen:
            continue
        if row is not None and _own_key(row, stored.slug) == key:
            chosen[key] = _source(key, row)
        else:
            chosen[key] = earlier[key]
            carried.append(f"source {key}: {DOI_SOURCE_NOTE}")
    order = [source.id for source in previous.sources] if previous else []
    return guided(chosen.values(), lambda s: s.id, [order], lambda s: id_number(s.id)), carried


def _source(key: str, row: Row) -> Source:
    external = row["externalIds"] or {}
    return Source(
        id=key,
        kind=row["kind"],
        sub_kind=row["evidenceKind"],
        title=row["title"],
        authors=list(row["authors"] or []),
        publisher=row["publisher"],
        year=row["year"],
        url=row["url"],
        doi=row["doi"],
        archived_url=external.get("archivedUrl"),
        language=external.get("language"),
        licence=row["licence"],
        access=external.get("access"),
        reliability=row["reliability"],
        retrieved_at=_day(row["retrievedAt"]),
    )


def _day(value: datetime | date | None) -> date | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC).date()
    return value
