from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import ARTISAN, STUDENT, role_value
from app.models import ArtisanProfile, StudentProfile, User
from app.models.enums import MINOR_AGE_BANDS
from app.research.testimony import RECORDING_NOTICE_VERSION, speaker

from . import reader_profiles
from .reader_profiles import ArtisanCraftRow, DistrictNames

__all__ = ["catalogue_rows", "craft_view", "district_view", "profile_view"]


def catalogue_rows(catalogue: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(row["slug"]): row for row in catalogue.get("crafts", [])}


def craft_view(craft: ArtisanCraftRow, rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    row = rows.get(craft.slug, {})
    return {
        "slug": craft.slug,
        "name": craft.name,
        "displayName": row.get("displayName") or craft.name,
        "familyLabel": row.get("familyLabel"),
        "kindLabel": row.get("kindLabel"),
    }


def district_view(district: DistrictNames | None) -> dict[str, Any] | None:
    if district is None:
        return None
    return {
        "lgd": district.lgd,
        "name": district.name,
        "state": {"lgd": district.state_lgd, "name": district.state_name},
    }


async def profile_view(session: AsyncSession, user: User, *, catalogue: Mapping[str, Any]) -> dict[str, Any]:
    role = role_value(user)
    student = await reader_profiles.student_profile(session, user.id) if role == STUDENT else None
    artisan = await reader_profiles.artisan_profile(session, user.id) if role == ARTISAN else None
    body: dict[str, Any] = {
        "role": role,
        "profileRequired": await reader_profiles.profile_required(session, user),
        "student": await _student_part(session, user, student) if role == STUDENT else None,
        "artisan": await _artisan_part(session, user, artisan, catalogue) if role == ARTISAN else None,
        "updatedAt": _iso(_updated(student, artisan)),
    }
    return body


async def _student_part(session: AsyncSession, user: User, profile: StudentProfile | None) -> dict[str, Any]:
    band = profile.ageBand if profile else None
    if await reader_profiles.guardian_confirmed(session, user.id):
        consent = "CONFIRMED"
    elif band in MINOR_AGE_BANDS:
        consent = "NEEDED"
    else:
        consent = "NOT_NEEDED"
    return {"ageBand": band, "gender": profile.gender if profile else None, "guardianConsent": consent}


async def _artisan_part(
    session: AsyncSession, user: User, profile: ArtisanProfile | None, catalogue: Mapping[str, Any]
) -> dict[str, Any]:
    rows = catalogue_rows(catalogue)
    crafts = [craft_view(craft, rows) for craft in await reader_profiles.artisan_crafts(session, user.id)]
    district = await reader_profiles.district_names(session, profile.districtLgd) if profile else None
    consent = await reader_profiles.recording_consent(session, user.id)
    return {
        "crafts": crafts,
        "district": district_view(district),
        "spokenLanguage": profile.spokenLanguage if profile else None,
        "credit": _credit(profile, crafts, district),
        "recordingConsent": (
            {"noticeVersion": consent.noticeVersion, "acceptedAt": _iso(consent.acceptedAt)}
            if consent
            else None
        ),
        "recordingNoticeVersion": RECORDING_NOTICE_VERSION,
    }


def _credit(
    profile: ArtisanProfile | None, crafts: list[dict[str, Any]], district: DistrictNames | None
) -> dict[str, Any]:
    if profile is None:
        return {"mode": None, "name": None, "shortName": None, "preview": None}
    preview = None
    if crafts and district is not None:
        preview = speaker(
            mode=profile.creditMode,
            name=profile.creditName,
            short_name=profile.creditShortName,
            craft=crafts[0]["displayName"],
            district=district.name,
            state=district.state_name,
        ).line
    return {
        "mode": profile.creditMode,
        "name": profile.creditName,
        "shortName": profile.creditShortName,
        "preview": preview,
    }


def _updated(student: StudentProfile | None, artisan: ArtisanProfile | None) -> datetime | None:
    row = student or artisan
    return row.updatedAt if row is not None else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
