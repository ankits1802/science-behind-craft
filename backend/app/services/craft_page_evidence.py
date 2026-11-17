from __future__ import annotations

from collections.abc import Sequence

from rapidfuzz import fuzz, process

from app.curation.duplicates import duplicate_key
from app.curation.limits import NEAR_DUPLICATE_MIN_SCORE, SECTION_SENTENCES_MAX
from app.models.enums import DISCIPLINES
from app.research.craft_page import (
    EvidenceEntry,
    EvidenceGroup,
    EvidenceSubject,
    OverviewSection,
    PageClaim,
    PageEvidence,
    PageSentence,
    SubjectRef,
)
from app.research.sections import DISCIPLINE_TITLES
from app.research.vocabulary import LEVEL_ORDER

__all__ = ["PROVENANCE_ORDER", "folded_claims", "page_evidence", "stored_overview_sections"]

PROVENANCE_ORDER = ("CURATED", "RESEARCHER", "FROM_ANSWERS", "SEED")
HYPOTHESIS = "HYPOTHESIS"
SUBJECT_ORDER = ("CRAFT", "STAGE", "MATERIAL", "TOOL", "PLACE", "COMMUNITY", "TERM", "CONCEPT")
SCORERS = (fuzz.ratio, fuzz.token_sort_ratio)


def _strength(claim: PageClaim) -> tuple[int, int, int, str, str]:
    return (
        PROVENANCE_ORDER.index(claim.provenance),
        LEVEL_ORDER[claim.level],
        -len(claim.citations),
        claim.text,
        str(claim.id),
    )


def folded_claims(claims: Sequence[PageClaim]) -> list[tuple[PageClaim, list[PageClaim]]]:
    parent = list(range(len(claims)))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    keys = [duplicate_key(claim.text) for claim in claims]
    for index, key in enumerate(keys):
        later = keys[index + 1 :]
        for scorer in SCORERS:
            for _match, _score, offset in process.extract(
                key, later, scorer=scorer, score_cutoff=NEAR_DUPLICATE_MIN_SCORE, limit=None
            ):
                parent[root(index + 1 + offset)] = root(index)
    clusters: dict[int, list[PageClaim]] = {}
    for index, claim in enumerate(claims):
        clusters.setdefault(root(index), []).append(claim)
    folded = []
    for members in clusters.values():
        ordered = sorted(members, key=_strength)
        folded.append((ordered[0], ordered[1:]))
    return sorted(folded, key=lambda pair: _strength(pair[0]))


def _entry(head: PageClaim, rest: Sequence[PageClaim]) -> EvidenceEntry:
    return EvidenceEntry(claim_id=head.id, folded_ids=[claim.id for claim in rest])


def page_evidence(claims: Sequence[PageClaim]) -> PageEvidence:
    facts = folded_claims([claim for claim in claims if claim.level != HYPOTHESIS])
    guesses = folded_claims([claim for claim in claims if claim.level == HYPOTHESIS])
    groups = []
    for discipline in DISCIPLINES:
        chosen = [(head, rest) for head, rest in facts if head.discipline == discipline]
        if chosen:
            groups.append(
                EvidenceGroup(
                    discipline=discipline, title=DISCIPLINE_TITLES[discipline], subjects=_subjects(chosen)
                )
            )
    ordered = sorted(guesses, key=lambda pair: (DISCIPLINES.index(pair[0].discipline), pair[0].text))
    return PageEvidence(groups=groups, hypotheses=[_entry(head, rest) for head, rest in ordered])


def _subjects(chosen: Sequence[tuple[PageClaim, list[PageClaim]]]) -> list[EvidenceSubject]:
    by_subject: dict[tuple[str, str], tuple[SubjectRef, list[EvidenceEntry]]] = {}
    for head, rest in chosen:
        subject = head.subject
        key = (str(subject.id), subject.name)
        by_subject.setdefault(key, (subject, []))[1].append(_entry(head, rest))
    ordered = sorted(
        by_subject.values(), key=lambda item: (SUBJECT_ORDER.index(item[0].kind), item[0].name.casefold())
    )
    return [EvidenceSubject(subject=subject, entries=entries) for subject, entries in ordered]


def stored_overview_sections(claims: Sequence[PageClaim]) -> list[OverviewSection]:
    facts = folded_claims([claim for claim in claims if claim.level != HYPOTHESIS])
    sections = []
    for discipline in DISCIPLINES:
        chosen = [head for head, _rest in facts if head.discipline == discipline][:SECTION_SENTENCES_MAX]
        if not chosen:
            continue
        sentences = [
            PageSentence(
                id=f"{discipline.lower()}.{number}",
                text=claim.text,
                level=claim.level,
                claim_ids=[claim.id],
                terms=[],
            )
            for number, claim in enumerate(chosen, start=1)
        ]
        sections.append(
            OverviewSection(
                discipline=discipline,
                title=DISCIPLINE_TITLES[discipline],
                basis="STORED_CLAIMS",
                sentences=sentences,
            )
        )
    return sections
