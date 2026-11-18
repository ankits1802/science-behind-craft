import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import profile_view as view
from app.services.reader_profiles import ArtisanCraftRow, DistrictNames

SHARED = Path(__file__).resolve().parents[3] / "shared"
UPDATED = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
CONSENTED = datetime(2026, 11, 18, 10, 5, tzinfo=UTC)
CATALOGUE = {
    "crafts": [
        {
            "slug": "kutch-ajrakh",
            "displayName": "Ajrakh",
            "familyLabel": "Printing and dyeing",
            "kindLabel": "Block printing",
        },
        {
            "slug": "kutch-bandhani",
            "displayName": "Bandhani",
            "familyLabel": "Printing and dyeing",
            "kindLabel": None,
        },
    ]
}


def golden(name: str) -> dict[str, Any]:
    return json.loads((SHARED / name).read_text(encoding="utf-8"))


def account(role: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, name="Ismail Mohammed Khatri")


def returning(value: Any) -> Any:
    async def answer(*_args: Any, **_kwargs: Any) -> Any:
        return value

    return answer


def fake_profiles(monkeypatch: pytest.MonkeyPatch, **answers: Any) -> None:
    defaults = {
        "student_profile": None,
        "artisan_profile": None,
        "artisan_crafts": [],
        "district_names": None,
        "recording_consent": None,
        "profile_required": False,
        "guardian_confirmed": False,
    }
    for name, value in {**defaults, **answers}.items():
        monkeypatch.setattr(view.reader_profiles, name, returning(value))


async def test_a_student_profile_matches_the_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    student = SimpleNamespace(ageBand="14_17", gender="UNSAID", updatedAt=UPDATED)
    fake_profiles(monkeypatch, student_profile=student)
    body = await view.profile_view(None, account("STUDENT"), catalogue=CATALOGUE)
    assert body == golden("profile.student.golden.json")


@pytest.mark.parametrize(
    ("band", "confirmed", "expected"),
    [("UNDER_14", False, "NEEDED"), ("23_PLUS", False, "NOT_NEEDED"), ("14_17", True, "CONFIRMED")],
)
async def test_guardian_consent_is_needed_only_for_an_unconfirmed_minor(
    monkeypatch: pytest.MonkeyPatch, band: str, confirmed: bool, expected: str
) -> None:
    fake_profiles(
        monkeypatch, student_profile=SimpleNamespace(ageBand=band, gender="WOMAN", updatedAt=UPDATED)
    )
    monkeypatch.setattr(view.reader_profiles, "guardian_confirmed", returning(confirmed))
    body = await view.profile_view(None, account("STUDENT"), catalogue=CATALOGUE)
    assert body["student"]["guardianConsent"] == expected


async def test_an_artisan_profile_matches_the_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = SimpleNamespace(
        districtLgd=449,
        spokenLanguage="gu",
        creditMode="FIRST_NAME",
        creditName="Ismail Mohammed Khatri",
        creditShortName="Ismail",
        updatedAt=UPDATED,
    )
    crafts = [
        ArtisanCraftRow(
            craft_id=uuid.uuid4(), slug="kutch-ajrakh", name="Ajrakh Block Printing", position=1, extra=None
        ),
        ArtisanCraftRow(
            craft_id=uuid.uuid4(), slug="kutch-bandhani", name="Bandhani", position=2, extra=None
        ),
    ]
    fake_profiles(
        monkeypatch,
        artisan_profile=profile,
        artisan_crafts=crafts,
        district_names=DistrictNames(lgd=449, name="Kachchh", state_lgd=24, state_name="Gujarat"),
        recording_consent=SimpleNamespace(noticeVersion="2026-11-18", acceptedAt=CONSENTED),
    )
    body = await view.profile_view(None, account("ARTISAN"), catalogue=CATALOGUE)
    assert body == golden("profile.artisan.golden.json")


async def test_other_roles_carry_neither_part_and_no_profile_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_profiles(monkeypatch)
    body = await view.profile_view(None, account("PROFESSOR"), catalogue=CATALOGUE)
    assert body == {
        "role": "PROFESSOR",
        "profileRequired": False,
        "student": None,
        "artisan": None,
        "updatedAt": None,
    }
