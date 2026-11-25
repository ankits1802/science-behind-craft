from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.open_work import OpenTask, WorkFilters, task_key
from app.research.picture_checks import CHECK_TASK_ACCEPTANCE, PICTURE_CHECK_TASK

from .picture_check_links import waiting_links

__all__ = ["CHECK_NEEDED", "picture_check_tasks"]

CHECK_NEEDED = (
    "{count} links of a searched picture to a fact were chosen by their words alone: no one has looked at "
    "the picture. Look at each and say whether it shows what its fact says, in this craft."
)
CHECK_PRIORITY = "HIGH"


async def picture_check_tasks(session: AsyncSession, filters: WorkFilters) -> list[OpenTask]:
    if filters.subject_filter() is not None:
        return []
    count = await waiting_links(session)
    if count == 0:
        return []
    return [
        OpenTask(
            key=task_key(PICTURE_CHECK_TASK, None),
            kind=PICTURE_CHECK_TASK,
            priority=CHECK_PRIORITY,
            subject=None,
            needed=CHECK_NEEDED.format(count=count),
            acceptance=CHECK_TASK_ACCEPTANCE,
            count=count,
        )
    ]
