from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.dossier import Dossier
from app.curation.reviewed_sections import ReviewedSection
from app.models import User

from . import knowledge_view
from .monograph_generated_sections import ReviewedBy, SectionOwner, person_wrote, publish_reviewed_section

__all__ = ["restore_reviewed_sections"]

logger = logging.getLogger(__name__)


async def restore_reviewed_sections(session: AsyncSession, dossier: Dossier, owner: SectionOwner) -> int:
    restored = 0
    for section in dossier.sections:
        if await person_wrote(session, owner, section.field):
            continue
        if not await _cites_shown_facts(session, section):
            logger.warning(
                "the reviewed %s section of %s cites facts readers cannot see, so it is not restored",
                section.field,
                dossier.slug,
            )
            continue
        reviewer = await session.get(User, section.reviewed_by) if section.reviewed_by else None
        reviewed = ReviewedBy(
            writer_id=None, reviewer_id=reviewer.id if reviewer else None, at=section.reviewed_at
        )
        await publish_reviewed_section(
            session, owner, section.field, section.sentences, reviewed, at_least=section.version
        )
        restored += 1
    return restored


async def _cites_shown_facts(session: AsyncSession, section: ReviewedSection) -> bool:
    cited = section.claim_ids()
    shown, _ = await knowledge_view.claims_by_id(session, cited)
    return all(claim_id in shown for claim_id in cited)
