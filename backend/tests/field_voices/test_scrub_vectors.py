import hashlib
from pathlib import Path
from typing import Any

import pytest

from app.services.field_voices_placements import IDENTITY_CAPTION
from app.services.field_voices_screen import field_personal_data_in, without_field_personal_data
from tests.field_voices.fixtures import RECORDED, SCRUB_VECTORS, recorded

PORTAL_MANIFEST_LINE = (
    "02a08df3faf65a4ba0c021f4f83934cf4e0d577406133fc726e89740b4844363  shared/field-voices-scrub-vectors.json"
)
PORTALS = ("designer-portal", "documentation-portal")
SIBLINGS = Path(__file__).resolve().parents[4]
VECTORS = recorded(SCRUB_VECTORS)


def own_hash() -> str:
    return hashlib.sha256((RECORDED / f"{SCRUB_VECTORS}.json").read_bytes()).hexdigest()


def test_the_vectors_are_the_bytes_both_portals_list_in_their_manifest() -> None:
    assert f"{own_hash()}  shared/{SCRUB_VECTORS}.json" == PORTAL_MANIFEST_LINE


@pytest.mark.parametrize("portal", PORTALS)
def test_a_checked_out_portal_lists_the_same_vectors(portal: str) -> None:
    manifest = SIBLINGS / portal / "shared" / "field-voices.sha256"
    if not manifest.is_file():
        pytest.skip(f"{portal} is not checked out beside KalaVigyan")
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert PORTAL_MANIFEST_LINE in lines


def pattern_only() -> list[dict[str, Any]]:
    return [case for case in VECTORS["scrub"] if not case["held"]]


def test_the_vectors_hold_pattern_only_cases() -> None:
    assert {case["name"] for case in pattern_only()} >= {
        "an email address",
        "a spoken email address",
        "a phone number with a gap",
        "an Aadhaar-like number",
        "an Aadhaar-like number with dots",
        "a PAN",
        "a voter ID",
        "an IFSC code",
    }


@pytest.mark.parametrize("case", pattern_only(), ids=lambda case: case["name"])
def test_kalavigyans_own_patterns_scrub_as_the_portals_do(case: dict[str, Any]) -> None:
    assert without_field_personal_data(case["text"]) == case["expected"]
    assert field_personal_data_in(case["expected"]) == []


@pytest.mark.parametrize("case", VECTORS["identityImage"], ids=lambda case: case["name"])
def test_kalavigyans_caption_pattern_withholds_what_the_portals_withhold(case: dict[str, Any]) -> None:
    assert bool(IDENTITY_CAPTION.search(case["text"])) is case["identity"]
