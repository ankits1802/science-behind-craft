from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, KnowledgePiece
from app.research.component_proposals import SUBJECT_LINK
from app.research.open_work_texts import counted
from app.research.page_layout import is_component_ref
from app.research.page_proposals import (
    COMPONENT,
    LAYOUT,
    REFUSED,
    PageBundle,
    PageComponent,
    PageLayoutPart,
    PageProposalResult,
    PageSubject,
    PartReport,
)

from .component_library_applies import registered_pieces
from .component_places_held import held_by_place
from .open_work_subjects import CATEGORY, WorkSubject, subject_by_key
from .page_held_facts import held_claims
from .page_layouts import subject_path

__all__ = ["BORROWED", "borrowed_problem", "held_refusal", "linked_labels", "placed_labels"]

BORROWED = (
    "{label} is borrowed from {owner} and its units cite {count} this page does not hold ({ids}). Build "
    "{page}'s own {kind} on its own facts in this draft or bundle, and place that instead."
)
SHARED_OWNER = "the shared library"
NOTHING_HELD = (
    "Nothing was held or proposed: the parts below place components this page cannot draw. Fix them and "
    "propose the page again."
)


def linked_labels(components: Sequence[PageComponent]) -> list[str]:
    return [
        component.proposal.extends
        for component in components
        if component.proposal.extension == SUBJECT_LINK and component.proposal.extends is not None
    ]


def placed_labels(components: Sequence[PageComponent], layout: PageLayoutPart | None) -> list[str]:
    if layout is None:
        return []
    own = {c.proposal.label for c in components if c.proposal.extension != SUBJECT_LINK}
    return list(dict.fromkeys(e.ref for e in layout.entries if is_component_ref(e.ref) and e.ref not in own))


async def borrowed_problem(session: AsyncSession, subject: WorkSubject, labels: Sequence[str]) -> str | None:
    wanted = list(dict.fromkeys(labels))
    if not wanted:
        return None
    rows = (
        await session.execute(
            select(KnowledgePiece, Craft.name)
            .outerjoin(Craft, Craft.id == KnowledgePiece.craftId)
            .where(KnowledgePiece.label.in_(wanted), *registered_pieces())
            .order_by(KnowledgePiece.label)
        )
    ).all()
    borrowed = [
        (piece, owner) for piece, owner in rows if subject.kind == CATEGORY or piece.craftId != subject.id
    ]
    if not borrowed:
        return None
    held = await held_claims(session, subject, [claim for piece, _ in borrowed for claim in piece.claimIds])
    placed = await held_by_place(session, subject, [piece for piece, _ in borrowed])
    found = [_problem(piece, owner, subject, held) for piece, owner in borrowed if piece.id not in placed]
    return " ".join(problem for problem in found if problem is not None) or None


async def held_refusal(session: AsyncSession, bundle: PageBundle, *, site: str) -> PageProposalResult | None:
    subject = await subject_by_key(session, bundle.subject.kind, bundle.subject.slug)
    refused: list[PartReport] = []
    for index, component in enumerate(bundle.components):
        problem = await borrowed_problem(session, subject, linked_labels([component]))
        if problem is not None:
            refused.append(PartReport(part=COMPONENT, index=index, outcome=REFUSED, message=problem))
    placed = placed_labels(bundle.components, bundle.layout)
    problem = await borrowed_problem(session, subject, placed)
    if problem is not None:
        refused.append(PartReport(part=LAYOUT, index=0, outcome=REFUSED, message=problem))
    if not refused:
        return None
    return PageProposalResult(
        subject=PageSubject(kind=subject.kind, slug=subject.slug),
        page_url=f"{site}{subject_path(subject)}",
        accepted=0,
        refused=len(refused),
        parts=refused,
        message=NOTHING_HELD,
    )


def _problem(
    piece: KnowledgePiece, owner: str | None, subject: WorkSubject, held: Collection[uuid.UUID]
) -> str | None:
    foreign = sorted({str(claim) for claim in piece.claimIds if claim not in held})
    if not foreign:
        return None
    return BORROWED.format(
        label=piece.label,
        owner=owner or SHARED_OWNER,
        count=counted(len(foreign), "fact"),
        ids=", ".join(foreign),
        page=subject.name,
        kind=piece.kind,
    )
