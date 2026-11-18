from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, release_connection
from app.core.deps import get_current_user
from app.core.roles import STUDENT, role_value
from app.models import User
from app.research.reading_style import ReadingStyle, reading_style_for
from app.services import reader_profiles

__all__ = ["PROFILE_REQUIRED_DETAIL", "PROFILE_REQUIRED_HEADER", "asker_style"]

PROFILE_REQUIRED_DETAIL = "Finish setting up your profile first."
PROFILE_REQUIRED_HEADER = "X-Profile-Required"


async def asker_style(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> ReadingStyle | None:
    if role_value(user) != STUDENT:
        return None
    profile = await reader_profiles.student_profile(session, user.id)
    await release_connection(session)
    if profile is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, PROFILE_REQUIRED_DETAIL, headers={PROFILE_REQUIRED_HEADER: "student"}
        )
    return reading_style_for(user, profile)
