from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminDistrict,
    ArtisanCraft,
    ArtisanProfile,
    ConsentRecord,
    StudentProfile,
    User,
    UserPreference,
)
from app.research.testimony import (
    CREDIT_NAME_MAX,
    CREDIT_SHORT_NAME_MAX,
    RECORDING_NOTICE_VERSION,
    credit_name_problem,
)

from . import audit, knowledge_view
from .reader_profiles import ARTISAN_RECORDING

__all__ = [
    "ArtisanChoice",
    "ProfileRefusal",
    "SavedArtisan",
    "StudentChoice",
    "record_recording_consent",
    "save_artisan",
    "save_student",
    "withdraw_recording_consents",
]

ACTIVE = "ACTIVE"
AUTO_LANGUAGE = "auto"
ADULT_DETAIL = "Confirm that you are 18 or older."
DUPLICATE_CRAFT_DETAIL = "Each craft is chosen once; {slug} is the same craft as another you chose."
UNKNOWN_CRAFT_DETAIL = "{slug} is not a craft in the catalogue."
UNKNOWN_DISTRICT_DETAIL = "District {lgd} is not in the register."
NOTICE_VERSION_DETAIL = "Agree to the current recording notice, version {version}."
CREDIT_FIELDS = ("creditMode", "creditName", "creditShortName")


class ProfileRefusal(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, kw_only=True)
class StudentChoice:
    age_band: str
    gender: str


@dataclass(frozen=True, kw_only=True)
class ArtisanChoice:
    craft_slugs: tuple[str, ...]
    district_lgd: int
    spoken_language: str
    adult_confirmed: bool
    credit_mode: str
    credit_name: str | None
    credit_short_name: str | None


@dataclass(frozen=True, kw_only=True)
class SavedArtisan:
    changed: tuple[str, ...]
    credit_changed: bool


async def save_student(
    session: AsyncSession, user: User, choice: StudentChoice, *, now: datetime
) -> tuple[str, ...]:
    profile = await session.get(StudentProfile, user.id, with_for_update=True)
    chosen = {"ageBand": choice.age_band, "gender": choice.gender}
    if profile is None:
        profile = StudentProfile(userId=user.id, completedAt=now, **chosen)
        session.add(profile)
        changed: tuple[str, ...] = tuple(chosen)
    else:
        changed = tuple(field for field, value in chosen.items() if getattr(profile, field) != value)
        for field, value in chosen.items():
            setattr(profile, field, value)
    if changed:
        await audit.record(
            session,
            action="profile.student_updated",
            actor=user,
            target_type="User",
            target_id=user.id,
            detail={"fields": list(changed)},
        )
    return changed


async def save_artisan(
    session: AsyncSession, user: User, choice: ArtisanChoice, *, now: datetime
) -> SavedArtisan:
    if choice.adult_confirmed is not True:
        raise ProfileRefusal(422, ADULT_DETAIL)
    craft_ids = await _resolved_crafts(session, choice.craft_slugs)
    if await session.get(AdminDistrict, choice.district_lgd) is None:
        raise ProfileRefusal(404, UNKNOWN_DISTRICT_DETAIL.format(lgd=choice.district_lgd))
    _check_credit(choice)
    profile = await session.get(ArtisanProfile, user.id, with_for_update=True)
    first_save = profile is None
    if profile is None:
        profile = ArtisanProfile(userId=user.id, adultConfirmedAt=now, completedAt=now)
        session.add(profile)
    before = {
        field: getattr(profile, field, None) for field in (*CREDIT_FIELDS, "districtLgd", "spokenLanguage")
    }
    _apply(profile, choice)
    changed = [field for field, value in before.items() if getattr(profile, field) != value]
    if await _replace_crafts(session, user.id, craft_ids):
        changed.append("crafts")
    if first_save:
        await _adopt_spoken_language(session, user.id, choice.spoken_language)
    await session.flush()
    if changed:
        await audit.record(
            session,
            action="profile.artisan_updated",
            actor=user,
            target_type="User",
            target_id=user.id,
            detail={"fields": sorted(changed)},
        )
    credit_changed = not first_save and any(
        field in changed for field in (*CREDIT_FIELDS, "districtLgd", "crafts")
    )
    return SavedArtisan(changed=tuple(sorted(changed)), credit_changed=credit_changed)


async def record_recording_consent(
    session: AsyncSession, user: User, *, notice_version: str, language: str, now: datetime
) -> ConsentRecord:
    if notice_version != RECORDING_NOTICE_VERSION:
        raise ProfileRefusal(409, NOTICE_VERSION_DETAIL.format(version=RECORDING_NOTICE_VERSION))
    record = ConsentRecord(
        userId=user.id, kind=ARTISAN_RECORDING, noticeVersion=notice_version, acceptedAt=now
    )
    session.add(record)
    await audit.record(
        session,
        action="profile.recording_consent_given",
        actor=user,
        target_type="User",
        target_id=user.id,
        detail={"noticeVersion": notice_version, "language": language},
    )
    await session.flush()
    return record


async def withdraw_recording_consents(session: AsyncSession, user: User, *, now: datetime) -> int:
    removed = await session.execute(
        update(ConsentRecord)
        .where(
            ConsentRecord.userId == user.id,
            ConsentRecord.kind == ARTISAN_RECORDING,
            ConsentRecord.withdrawnAt.is_(None),
        )
        .values(withdrawnAt=now)
    )
    await audit.record(
        session,
        action="profile.recording_consent_withdrawn",
        actor=user,
        target_type="User",
        target_id=user.id,
    )
    return int(removed.rowcount or 0)


async def _resolved_crafts(session: AsyncSession, slugs: tuple[str, ...]) -> list[uuid.UUID]:
    resolved: list[uuid.UUID] = []
    for slug in slugs:
        craft = await knowledge_view.resolve_craft(session, slug.strip())
        if craft is None or craft.status != ACTIVE:
            raise ProfileRefusal(404, UNKNOWN_CRAFT_DETAIL.format(slug=slug))
        if craft.id in resolved:
            raise ProfileRefusal(422, DUPLICATE_CRAFT_DETAIL.format(slug=slug))
        resolved.append(craft.id)
    return resolved


def _check_credit(choice: ArtisanChoice) -> None:
    if choice.credit_mode == "FULL_NAME":
        problem = credit_name_problem(choice.credit_name, limit=CREDIT_NAME_MAX)
    elif choice.credit_mode == "FIRST_NAME":
        problem = credit_name_problem(choice.credit_short_name, limit=CREDIT_SHORT_NAME_MAX)
    else:
        problem = None
    if problem is not None:
        raise ProfileRefusal(422, problem)


def _apply(profile: ArtisanProfile, choice: ArtisanChoice) -> None:
    profile.districtLgd = choice.district_lgd
    profile.spokenLanguage = choice.spoken_language
    profile.creditMode = choice.credit_mode
    if choice.credit_name:
        profile.creditName = choice.credit_name.strip()
    if choice.credit_short_name:
        profile.creditShortName = choice.credit_short_name.strip()


async def _replace_crafts(session: AsyncSession, user_id: uuid.UUID, craft_ids: list[uuid.UUID]) -> bool:
    current = list(
        await session.scalars(
            select(ArtisanCraft.craftId).where(ArtisanCraft.userId == user_id).order_by(ArtisanCraft.position)
        )
    )
    if current == craft_ids:
        return False
    await session.execute(delete(ArtisanCraft).where(ArtisanCraft.userId == user_id))
    await session.flush()
    for position, craft_id in enumerate(craft_ids, start=1):
        session.add(ArtisanCraft(userId=user_id, craftId=craft_id, position=position))
    return True


async def _adopt_spoken_language(session: AsyncSession, user_id: uuid.UUID, language: str) -> None:
    preference = (
        await session.execute(select(UserPreference).where(UserPreference.userId == user_id))
    ).scalar_one_or_none()
    if preference is None:
        session.add(UserPreference(userId=user_id, answerLanguage=language))
    elif preference.answerLanguage == AUTO_LANGUAGE:
        preference.answerLanguage = language
