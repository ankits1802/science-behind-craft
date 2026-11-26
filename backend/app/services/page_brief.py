from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.knowledge_api import Fact
from app.research.open_work import OpenTask
from app.research.page_brief import BriefInput, PageBrief, page_brief
from app.retrieval.citation_access import HeldFacts

from . import category_knowledge, coverage_reads, knowledge_api
from .compose_components import ComposeDeps
from .monograph_document import stored_document
from .open_work_subjects import CATEGORY, WorkSubject
from .page_layouts import layout_of
from .page_report_held import held_shapes

__all__ = ["ReadBrief", "read_page_brief"]

ReadBrief = tuple[PageBrief, list[OpenTask]]


async def read_page_brief(
    session: AsyncSession, subject: WorkSubject, *, site: str, held: HeldFacts, cursor: str | None
) -> ReadBrief:
    facts = await _facts(session, subject, held)
    if cursor is not None:
        return page_brief(BriefInput(subject.name, subject.slug, facts), cursor), []
    read = await coverage_reads.read_subject_coverage(session, subject.kind, subject.slug, site=site)
    given = BriefInput(
        name=subject.name,
        slug=subject.slug,
        facts=facts,
        coverage=read.coverage,
        document=await stored_document(session, subject.kind, subject.slug),
        layout=await layout_of(session, subject),
        held=await held_shapes(session, ComposeDeps(), subject.kind, subject.slug),
    )
    return page_brief(given), list(read.open_work)


async def _facts(session: AsyncSession, subject: WorkSubject, held: HeldFacts) -> list[Fact]:
    if subject.kind == CATEGORY:
        return await category_knowledge.category_fact_list(session, subject)
    return await knowledge_api.fact_list(session, subject.slug, held=held)
