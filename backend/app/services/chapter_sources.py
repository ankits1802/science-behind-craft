from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from app.research.citations import AnswerSentence, SourceRef
from app.research.craft_chapters import Borrowed
from app.research.craft_masthead import PageSource
from app.research.craft_page import PageClaim, PageQuestion
from app.research.craft_parts import (
    SOURCE_GROUPS,
    OpenQuestion,
    OpenQuestionsPart,
    PictureCredit,
    SearchedPart,
    SourceGroupList,
    SourceListPart,
)
from app.research.datasets import DatasetRef
from app.research.media_refs import MediaRef

from .chapter_context import ChapterContext
from .chapter_draft import ChapterDraft, Drafted

__all__ = ["GROUP_TITLES", "SourceOrigins", "page_sources", "source_list", "sources_chapter"]

KEY = "sources"
KIND_GROUPS: Mapping[str, str] = MappingProxyType(
    {
        "GI_JOURNAL": "GOVERNMENT",
        "GOVERNMENT_REPORT": "GOVERNMENT",
        "PAPER": "SCHOLARSHIP",
        "BOOK": "SCHOLARSHIP",
        "BOOK_CHAPTER": "SCHOLARSHIP",
        "DATASET": "SCHOLARSHIP",
        "COMPOUND_RECORD": "COMPOUND_RECORDS",
        "FIELD_TESTIMONY": "FIELD",
    }
)
GROUP_TITLES: Mapping[str, str] = MappingProxyType(
    {
        "GOVERNMENT": "Government records",
        "SCHOLARSHIP": "Scholarship",
        "MUSEUM": "Museums and archives",
        "WEB_AND_PRESS": "Web and press",
        "FIELD": "Field interviews",
        "FAMILY": "From the {family} family monograph",
        "KIN": "From related monographs",
        "LIBRARY": "From the KalaVigyan compound library",
        "COMPOUND_RECORDS": "Compound records, from PubChem",
    }
)
MUSEUM_WORDS = ("museum", "archive", "gallery")
WEB_AND_PRESS = "WEB_AND_PRESS"
SEED = "SEED"
BORROWED_GROUPS = {"FAMILY", "KIN"}


@dataclass(frozen=True)
class SourceOrigins:
    family: Mapping[str, Borrowed] = field(default_factory=dict)
    kin: Mapping[str, Borrowed] = field(default_factory=dict)
    library: frozenset[str] = frozenset()
    records: frozenset[str] = frozenset()


def sources_chapter(ctx: ChapterContext, questions: Sequence[PageQuestion]) -> ChapterDraft:
    items: list[Drafted] = []
    asked = [_question(ctx, question) for question in questions]
    if asked:
        items.append(Drafted.of_part(OpenQuestionsPart(kind="open_questions", questions=asked)))
    curated = ctx.records.curated
    if curated is not None and curated.coverage == "THIN" and curated.searched:
        searched = [{"query": item.query, "site": item.site} for item in curated.searched]
        items.append(Drafted.of_part(SearchedPart.model_validate({"kind": "searched", "searched": searched})))
    return ChapterDraft(KEY, None, items)


def source_list(
    family: str | None, listing: tuple[Sequence[PageSource], Sequence[DatasetRef], Sequence[MediaRef]]
) -> SourceListPart | None:
    sources, datasets, pictures = listing
    groups = _groups(sources, family)
    if not groups:
        return None
    credits = [PictureCredit(media_id=media.id, credit=_credit(media)) for media in pictures]
    return SourceListPart(kind="source_list", groups=groups, datasets=list(datasets), pictures=credits)


def page_sources(
    shown: tuple[Iterable[AnswerSentence], Sequence[str]],
    later: tuple[Sequence[PageClaim], Sequence[str]],
    refs: Mapping[str, SourceRef],
    origins: SourceOrigins,
) -> list[PageSource]:
    sentences, cited = list(shown[0]), shown[1]
    claims, voiced = later
    supports = Counter(sid for s in sentences for sid in dict.fromkeys(c.source_id for c in s.citations))
    order = dict.fromkeys(cited)
    order.update(dict.fromkeys(c.source_id for claim in claims for c in claim.citations))
    order.update(dict.fromkeys(voiced))
    return [_page_source(refs[sid], supports[sid], origins) for sid in order if sid in refs]


def _page_source(ref: SourceRef, supports: int, origins: SourceOrigins) -> PageSource:
    group, borrowed = _group(ref, origins)
    plain: dict[str, Any] = ref.model_dump(by_alias=True)
    return PageSource.model_validate({**plain, "group": group, "from": borrowed, "supports": supports})


def _group(ref: SourceRef, origins: SourceOrigins) -> tuple[str, Borrowed | None]:
    if ref.id in origins.records or ref.kind == "COMPOUND_RECORD":
        return "COMPOUND_RECORDS", None
    if ref.id in origins.family:
        return "FAMILY", origins.family[ref.id]
    if ref.id in origins.kin:
        return "KIN", origins.kin[ref.id]
    if ref.id in origins.library:
        return "LIBRARY", None
    if ref.kind in KIND_GROUPS:
        return KIND_GROUPS[ref.kind], None
    publisher = (ref.publisher or "").casefold()
    return ("MUSEUM" if any(word in publisher for word in MUSEUM_WORDS) else WEB_AND_PRESS), None


def _groups(sources: Sequence[PageSource], family: str | None) -> list[SourceGroupList]:
    groups = []
    for group in SOURCE_GROUPS:
        ids = [source.id for source in sources if source.group == group]
        if ids:
            title = GROUP_TITLES[group].format(family=family or "craft")
            groups.append(SourceGroupList(group=group, title=title, source_ids=ids))
    return groups


def _question(ctx: ChapterContext, question: PageQuestion) -> OpenQuestion:
    sentences = [
        s
        for n, claim_id in enumerate(question.claim_ids, start=1)
        if (s := ctx.sentence(claim_id, f"open-{question.key or 'q'}.{n}"))
    ]
    return OpenQuestion(
        key=question.key, question=question.question, settled_by=question.settled_by, sentences=sentences
    )


def _credit(media: MediaRef) -> str:
    parts = [part for part in (media.author, media.licence, f"via {media.site}") if part]
    return media.credit or ", ".join(parts)
