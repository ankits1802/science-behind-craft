from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING

from .chapter_keys import CHAPTER_KEYS
from .citations import Citation
from .media_refs import MediaRef

if TYPE_CHECKING:
    from .craft_page import CraftPage, PageEvidence

__all__ = [
    "chapters_agree",
    "cited_ids",
    "evidence_covers",
    "listed_once",
    "shown_pictures",
    "v2_parts_agree",
]

HYPOTHESIS = "HYPOTHESIS"
HERO = "HERO"


def listed_once(levels: dict[uuid.UUID, str], ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    repeated = sorted(str(claim_id) for claim_id, count in Counter(ids).items() if count > 1)
    if repeated:
        raise ValueError(f"claims are listed once each; repeated: {', '.join(repeated)}")
    return levels


def cited_ids(citations: Iterable[Citation]) -> Iterator[uuid.UUID]:
    for citation in citations:
        yield uuid.UUID(citation.claim_id)


def evidence_covers(evidence: PageEvidence, levels: Mapping[uuid.UUID, str]) -> None:
    seen: list[uuid.UUID] = []
    for entry, hypotheses in evidence.entries():
        for claim_id in [entry.claim_id, *entry.folded_ids]:
            if claim_id not in levels:
                raise ValueError(f"evidence lists claim {claim_id}, which the page does not list")
            if (levels[claim_id] == HYPOTHESIS) != hypotheses:
                raise ValueError(f"claim {claim_id} is filed with the wrong kind: hypotheses stand apart")
            seen.append(claim_id)
    if sorted(map(str, seen)) != sorted(map(str, levels)):
        raise ValueError("all evidence lists every claim of the page exactly once")


def chapters_agree(page: CraftPage) -> None:
    keys = [chapter.key for chapter in page.chapters]
    if len(set(keys)) != len(keys):
        raise ValueError("each chapter appears once")
    if keys != [key for key in CHAPTER_KEYS if key in keys]:
        raise ValueError("chapters keep the monograph's order")
    shown: dict[str, str] = {}
    for media in shown_pictures(page):
        for key in (str(media.id), media.image_url):
            if key in shown:
                raise ValueError(f"a page shows each picture once; {media.title!r} is shown twice")
            shown[key] = media.title
    contributed = [plate.contribution_id for plate in page.contributed_plates()]
    if len(set(contributed)) != len(contributed):
        raise ValueError("a page shows each contributed picture once")


def shown_pictures(page: CraftPage) -> Iterator[MediaRef]:
    if page.masthead.picture is not None:
        yield page.masthead.picture.media
    for chapter in page.chapters:
        for plate in chapter.plates():
            yield plate.media
        for item in chapter.items:
            yield from item.shown_media()


def v2_parts_agree(page: CraftPage) -> None:
    if sum(1 for picture in page.pictures if picture.role == HERO) > 1:
        raise ValueError("a page has one hero picture at most")
    keys = [row.key for row in page.sources_differ]
    if len(keys) != len(set(keys)):
        raise ValueError("each row of sources differ has its own key")
    unknown = {key for stage in page.process.stages for key in stage.differ} - set(keys)
    if unknown:
        raise ValueError(
            f"stages point to sources-differ rows the page does not list: {', '.join(sorted(unknown))}"
        )
    pointed = {group.place_key for group in page.communities if group.place_key}
    pointed |= {step.place.key for step in page.environment if step.place}
    unlisted = pointed - {place.key for place in page.places}
    if unlisted:
        raise ValueError(f"parts point to places the page does not list: {', '.join(sorted(unlisted))}")
    if page.craft.slug in {relative.craft.slug for relative in page.same_family}:
        raise ValueError("a craft is not its own relative")
    totals = page.field_voices_total
    if len(page.voices) > totals.quotes or len(page.field_photos) > totals.images:
        raise ValueError("the page shows no more field voices than it counts")
