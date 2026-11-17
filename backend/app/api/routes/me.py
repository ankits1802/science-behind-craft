from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth
from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import User, UserPreference
from app.schemas.preferences import PreferencesUpdate

router = APIRouter(tags=["me"])

router.add_api_route("/me", auth.me, methods=["GET"])

PREFERENCE_FIELDS = ("theme", "reducedMotion", "largerText", "highContrast", "answerLanguage", "alertDigest")


def serialize_preferences(row: UserPreference) -> dict[str, Any]:
    return {
        "theme": row.theme,
        "reducedMotion": row.reducedMotion,
        "largerText": row.largerText,
        "highContrast": row.highContrast,
        "answerLanguage": row.answerLanguage,
        "alertDigest": row.alertDigest,
        "alertDigestOffered": get_settings().alert_digest_enabled,
        "updatedAt": row.updatedAt.isoformat() if row.updatedAt else None,
    }


async def preferences_for(session: AsyncSession, user: User) -> UserPreference:
    query = select(UserPreference).where(UserPreference.userId == user.id)
    row = (await session.execute(query)).scalar_one_or_none()
    if row is not None:
        return row
    await session.execute(
        insert(UserPreference).values(userId=user.id).on_conflict_do_nothing(index_elements=["userId"])
    )
    await session.flush()
    return (await session.execute(query.execution_options(populate_existing=True))).scalar_one()


@router.get("/preferences/me")
async def get_preferences(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    row = await preferences_for(session, user)
    body = serialize_preferences(row)
    await session.commit()
    return body


@router.put("/preferences/me")
async def put_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await preferences_for(session, user)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field in PREFERENCE_FIELDS:
        if field in changes:
            setattr(row, field, changes[field])
    await session.commit()
    await session.refresh(row)
    return serialize_preferences(row)
