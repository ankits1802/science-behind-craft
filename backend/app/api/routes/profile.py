from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.profile_bodies import ArtisanProfileUpdate, RecordingConsentRequest, StudentProfileUpdate
from app.api.public_deps import public_reader
from app.api.routes.crafts import catalogue_cache
from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.kept_value import KeptValue
from app.core.roles import ARTISAN, STUDENT, role_value
from app.data.district_register import load_listed_places
from app.models import User
from app.research.vocabulary import AnswerLanguage
from app.services import craft_catalogue, testimony_writes
from app.services.object_store import media_bucket
from app.services.profile_view import profile_view
from app.services.profile_writes import (
    ArtisanChoice,
    ProfileRefusal,
    StudentChoice,
    record_recording_consent,
    save_artisan,
    save_student,
    withdraw_recording_consents,
)
from app.voice.artisan_notice import recording_notice

router = APIRouter(tags=["profile"])

PLACES_CACHE = "public, max-age=86400"
STUDENT_ONLY = "This profile is for student accounts."
ARTISAN_ONLY = "This profile is for artisan accounts."


def _refuse_unless_role(user: User, role: str, detail: str) -> None:
    if role_value(user) != role:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)


def _refused(refusal: ProfileRefusal) -> HTTPException:
    return HTTPException(refusal.status, refusal.detail)


async def _view(session: AsyncSession, user: User, kept: KeptValue[dict[str, Any]]) -> dict[str, Any]:
    catalogue = await craft_catalogue.reader_catalogue(session, kept)
    return await profile_view(session, user, catalogue=catalogue)


@router.get("/profile/me")
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    kept: KeptValue[dict[str, Any]] = Depends(catalogue_cache),
) -> dict[str, Any]:
    return await _view(session, user, kept)


@router.put("/profile/me/student")
async def put_student_profile(
    payload: StudentProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    kept: KeptValue[dict[str, Any]] = Depends(catalogue_cache),
) -> dict[str, Any]:
    _refuse_unless_role(user, STUDENT, STUDENT_ONLY)
    choice = StudentChoice(age_band=payload.ageBand, gender=payload.gender)
    await save_student(session, user, choice, now=datetime.now(UTC))
    await session.commit()
    return await _view(session, user, kept)


@router.put("/profile/me/artisan")
async def put_artisan_profile(
    payload: ArtisanProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    kept: KeptValue[dict[str, Any]] = Depends(catalogue_cache),
) -> dict[str, Any]:
    _refuse_unless_role(user, ARTISAN, ARTISAN_ONLY)
    choice = ArtisanChoice(
        craft_slugs=tuple(payload.craftSlugs),
        district_lgd=payload.districtLgd,
        spoken_language=payload.spokenLanguage,
        adult_confirmed=payload.adultConfirmed,
        credit_mode=payload.credit.mode,
        credit_name=payload.credit.name,
        credit_short_name=payload.credit.shortName,
    )
    try:
        saved = await save_artisan(session, user, choice, now=datetime.now(UTC))
    except ProfileRefusal as refusal:
        await session.rollback()
        raise _refused(refusal) from None
    if saved.credit_changed:
        await testimony_writes.rewrite_credit(session, user)
        await testimony_writes.rescreen_contributions(session, user.id)
    await session.commit()
    return await _view(session, user, kept)


@router.get("/artisan/recording-notice")
async def get_recording_notice(
    language: AnswerLanguage | None = None, user: User = Depends(get_current_user)
) -> dict[str, Any]:
    _refuse_unless_role(user, ARTISAN, ARTISAN_ONLY)
    return recording_notice(language, get_settings().mail_reply_to)


@router.post("/profile/me/recording-consent", status_code=status.HTTP_201_CREATED)
async def post_recording_consent(
    payload: RecordingConsentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _refuse_unless_role(user, ARTISAN, ARTISAN_ONLY)
    now = datetime.now(UTC)
    try:
        record = await record_recording_consent(
            session, user, notice_version=payload.noticeVersion, language=payload.language, now=now
        )
    except ProfileRefusal as refusal:
        raise _refused(refusal) from None
    await session.commit()
    return {"kind": record.kind, "noticeVersion": record.noticeVersion, "acceptedAt": now.isoformat()}


@router.delete("/profile/me/recording-consent")
async def delete_recording_consent(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    now = datetime.now(UTC)
    withdrawn = await testimony_writes.withdraw_everything(session, media_bucket(), user, now=now)
    await withdraw_recording_consents(session, user, now=now)
    await session.commit()
    return {
        "withdrawnContributions": withdrawn.withdrawn_contributions,
        "deletedConversations": withdrawn.deleted_conversations,
    }


@router.get("/places/districts")
async def get_districts(response: Response, reader: User | None = Depends(public_reader)) -> dict[str, Any]:
    response.headers["Cache-Control"] = PLACES_CACHE
    return {"states": list(load_listed_places())}
