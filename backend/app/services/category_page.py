from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from app.research.blocks import ProseBlock
from app.research.category_page import (
    CATEGORY_LIST_SCHEMA_VERSION,
    CATEGORY_PAGE_SCHEMA_VERSION,
    CategoryClaim,
    CategoryCuration,
    CategoryDiffer,
    CategoryFact,
    CategoryHero,
    CategoryList,
    CategoryOverview,
    CategoryPage,
    CategoryPicture,
    CategoryQuestion,
    CategoryRef,
    CategorySearch,
    CategorySection,
    CategorySentence,
    CategorySubCategory,
    CategorySummary,
    CategoryTerm,
    MemberCraft,
    NumberedSource,
    SubCategoryCount,
    category_path,
    referenced_claims,
)
from app.research.citations import AnswerSentence, Citation, SourceRef
from app.research.knowledge_pieces import KnowledgePiece
from app.research.media_refs import MediaRef
from app.research.sections import DISCIPLINE_TITLES
from app.research.vocabulary import weakest_level

from .category_register import CategoryRecord, MemberRecord
from .curated_category_index import CuratedCategoryPage, IndexSentenceRefs
from .knowledge_view import ClaimView

__all__ = ["CategoryClaimFacts", "CategoryPageRecords", "category_list", "category_page", "category_summary"]

HYPOTHESIS = "HYPOTHESIS"
INLINE = "INLINE"

Levels = Mapping[uuid.UUID, str]


@dataclass(frozen=True)
class CategoryClaimFacts:
    discipline: str
    sources_differ: bool


@dataclass(frozen=True)
class CategoryPageRecords:
    category: CategoryRecord
    curated: CuratedCategoryPage | None = None
    views: tuple[ClaimView, ...] = ()
    facts: Mapping[uuid.UUID, CategoryClaimFacts] = field(default_factory=dict)
    sources: Mapping[str, SourceRef] = field(default_factory=dict)
    pieces: Mapping[uuid.UUID, KnowledgePiece] = field(default_factory=dict)
    media: Mapping[uuid.UUID, MediaRef] = field(default_factory=dict)


def category_page(records: CategoryPageRecords) -> CategoryPage:
    views = {view.id: view for view in records.views if view.id in records.facts}
    levels = {claim_id: view.level for claim_id, view in views.items()}
    curated = records.curated
    overview = _overview(records, levels)
    differ = _differ(curated, levels)
    glossary = _glossary(curated, levels)
    pictures = _pictures(records, levels)
    questions = _questions(records, levels)
    order = dict.fromkeys(referenced_claims(overview, [*differ, *glossary, *pictures, *questions]))
    claims = [_claim(views[claim_id], records.facts[claim_id]) for claim_id in order]
    return CategoryPage(
        schema_version=CATEGORY_PAGE_SCHEMA_VERSION,
        category=_category_ref(records.category),
        curated=curated is not None,
        curation=_curation(curated),
        hero=next(
            (CategoryHero(media=p.media, caption=p.caption) for p in pictures if p.media.display == INLINE),
            None,
        ),
        overview=overview,
        sub_categories=_sub_categories(records.category, overview, questions),
        sources_differ=differ,
        glossary=glossary,
        pictures=pictures,
        open_questions=questions,
        claims=claims,
        sources=_numbered(claims, records.sources),
    )


def category_summary(records: CategoryPageRecords) -> tuple[CategorySummary, list[SourceRef]]:
    page = category_page(records)
    lede = page.overview.lede[0] if page.overview.lede else None
    claims = {claim.id: claim for claim in page.claims}
    citations = [c for claim_id in lede.claim_ids for c in claims[claim_id].citations] if lede else []
    cited = {citation.source_id for citation in citations}
    summary = CategorySummary(
        **page.category.model_dump(),
        curated=page.curated,
        sub_categories=[
            SubCategoryCount(slug=sub.slug, name=sub.name, label=sub.label, craft_count=sub.craft_count)
            for sub in page.sub_categories
        ],
        hero=page.hero,
        lede=None
        if lede is None
        else AnswerSentence(id=lede.id, text=lede.text, level=lede.level, citations=citations),
    )
    sources = [SourceRef.model_validate(source.model_dump(exclude={"number"})) for source in page.sources]
    return summary, [source for source in sources if source.id in cited]


def category_list(records: Sequence[CategoryPageRecords]) -> CategoryList:
    summaries: list[CategorySummary] = []
    sources: dict[str, SourceRef] = {}
    for one in records:
        summary, cited = category_summary(one)
        summaries.append(summary)
        sources.update((source.id, source) for source in cited if source.id not in sources)
    return CategoryList(
        schema_version=CATEGORY_LIST_SCHEMA_VERSION, categories=summaries, sources=list(sources.values())
    )


def _category_ref(category: CategoryRecord) -> CategoryRef:
    return CategoryRef(
        slug=category.slug,
        name=category.name,
        label=category.label,
        palette=category.palette,
        path=category_path(category.slug),
        craft_count=category.craft_count(),
    )


def _curation(curated: CuratedCategoryPage | None) -> CategoryCuration | None:
    if curated is None:
        return None
    return CategoryCuration(
        version=curated.version,
        curated_at=curated.curated_at,
        coverage=curated.coverage,
        searched=[CategorySearch(query=item.query, site=item.site) for item in curated.searched],
    )


def _kept(claim_ids: Iterable[uuid.UUID], levels: Levels) -> list[uuid.UUID]:
    return [claim_id for claim_id in dict.fromkeys(claim_ids) if claim_id in levels]


def _all_shown(claim_ids: Sequence[uuid.UUID], levels: Levels) -> bool:
    return bool(claim_ids) and all(claim_id in levels for claim_id in claim_ids)


def _overview(records: CategoryPageRecords, levels: Levels) -> CategoryOverview:
    curated = records.curated
    if curated is None:
        return CategoryOverview(lede=[], key_facts=[], sections=[])
    shown = _Shown(levels, curated.refs(), records.category)
    lede_id = curated.overview.lede_piece_id
    sections = []
    for section in curated.overview.sections:
        sentences = shown.sentences(records.pieces.get(section.piece_id))
        if sentences:
            title = DISCIPLINE_TITLES[section.discipline]
            sections.append(CategorySection(discipline=section.discipline, title=title, sentences=sentences))
    facts = [
        CategoryFact(label=fact.label, value=fact.value, claim_ids=fact.claim_ids)
        for fact in curated.overview.key_facts
        if _all_shown(fact.claim_ids, levels)
    ]
    lede = shown.sentences(records.pieces.get(lede_id)) if lede_id else []
    return CategoryOverview(lede=lede, key_facts=facts, sections=sections)


@dataclass(frozen=True)
class _Shown:
    levels: Levels
    refs: Mapping[str, IndexSentenceRefs]
    category: CategoryRecord

    def sentences(self, piece: KnowledgePiece | None) -> list[CategorySentence]:
        if piece is None or not isinstance(piece.payload, ProseBlock):
            return []
        shown = []
        for sentence in piece.payload.sentences:
            claim_ids = list(dict.fromkeys(uuid.UUID(citation.claim_id) for citation in sentence.citations))
            if not _all_shown(claim_ids, self.levels):
                continue
            level = weakest_level(self.levels[claim_id] for claim_id in claim_ids)
            if level != HYPOTHESIS:
                subs, crafts = self._named(sentence.id)
                shown.append(
                    CategorySentence(
                        id=sentence.id,
                        text=sentence.text,
                        level=level,
                        claim_ids=claim_ids,
                        terms=sentence.terms,
                        sub_categories=subs,
                        crafts=crafts,
                    )
                )
        return shown

    def _named(self, sentence_id: str) -> tuple[list[str], list[str]]:
        ref = self.refs.get(sentence_id)
        if ref is None:
            return [], []
        subs = {sub.slug for sub in self.category.sub_categories}
        members = self.category.member_slugs()
        return [s for s in ref.sub_categories if s in subs], [c for c in ref.crafts if c in members]


def _differ(curated: CuratedCategoryPage | None, levels: Levels) -> list[CategoryDiffer]:
    rows = [(item.about, _kept(item.claim_ids, levels)) for item in curated.conflicts] if curated else []
    return [CategoryDiffer(about=about, claim_ids=ids) for about, ids in rows if len(ids) >= 2]


def _glossary(curated: CuratedCategoryPage | None, levels: Levels) -> list[CategoryTerm]:
    return [
        CategoryTerm(
            key=term.term_key,
            label=term.names[0] if term.names else term.term,
            names=term.names,
            meaning=term.meaning,
            language=term.language,
            script=term.script,
            claim_ids=_kept(term.claim_ids, levels),
        )
        for term in (curated.glossary if curated else [])
    ]


def _pictures(records: CategoryPageRecords, levels: Levels) -> list[CategoryPicture]:
    shown = []
    for picture in records.curated.pictures if records.curated else []:
        media = records.media.get(picture.media_ref_id)
        claims = _kept(picture.claim_ids, levels)
        if media is not None and claims:
            shown.append(CategoryPicture(media=media, caption=picture.caption, claim_ids=claims))
    return shown


def _questions(records: CategoryPageRecords, levels: Levels) -> list[CategoryQuestion]:
    subs = {sub.slug for sub in records.category.sub_categories}
    shown = []
    for item in records.curated.open_questions if records.curated else []:
        claims = _kept(item.claim_ids, levels)
        named = [slug for slug in item.sub_categories if slug in subs]
        if claims or (named and not item.claim_ids):
            shown.append(
                CategoryQuestion(
                    key=item.key,
                    question=item.question,
                    settled_by=item.settled_by,
                    claim_ids=claims,
                    sub_categories=named,
                )
            )
    return shown


def _sub_categories(
    category: CategoryRecord, overview: CategoryOverview, questions: Sequence[CategoryQuestion]
) -> list[CategorySubCategory]:
    sentences = overview.sentences()
    return [
        CategorySubCategory(
            slug=sub.slug,
            name=sub.name,
            label=sub.label,
            craft_count=sub.craft_count(),
            crafts=[_member(craft) for craft in sub.crafts],
            sentence=next((s for s in sentences if sub.slug in s.sub_categories), None),
            open_question=next((q.key for q in questions if sub.slug in q.sub_categories), None),
        )
        for sub in category.sub_categories
    ]


def _member(craft: MemberRecord) -> MemberCraft:
    return MemberCraft(
        slug=craft.slug,
        name=craft.name,
        path=f"/crafts/{craft.slug}",
        gi_status=craft.gi_status,
        catch_all=craft.catch_all,
        curated=craft.curated,
    )


def _claim(view: ClaimView, facts: CategoryClaimFacts) -> CategoryClaim:
    return CategoryClaim(
        id=view.id,
        text=view.text,
        level=view.level,
        discipline=facts.discipline,
        sources_differ=facts.sources_differ,
        citations=[Citation.model_validate(citation) for citation in view.citations],
    )


def _numbered(claims: Sequence[CategoryClaim], known: Mapping[str, SourceRef]) -> list[NumberedSource]:
    order = dict.fromkeys(citation.source_id for claim in claims for citation in claim.citations)
    return [
        NumberedSource.model_validate({**known[source_id].model_dump(), "number": number})
        for number, source_id in enumerate(order, start=1)
    ]
