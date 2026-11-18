import pytest
from pydantic import ValidationError

from app.api.profile_bodies import ArtisanProfileUpdate, RecordingConsentRequest, StudentProfileUpdate
from app.data.district_register import load_listed_places

ARTISAN_BODY = {
    "craftSlugs": ["kutch-ajrakh"],
    "districtLgd": 449,
    "spokenLanguage": "gu",
    "adultConfirmed": True,
    "credit": {"mode": "FIRST_NAME", "shortName": "Ismail"},
}


@pytest.mark.parametrize("band", ["UNDER_14", "14_17", "18_22", "23_PLUS"])
def test_every_age_band_is_accepted(band: str) -> None:
    assert StudentProfileUpdate(ageBand=band, gender="UNSAID").ageBand == band


@pytest.mark.parametrize("gender", ["WOMAN", "MAN", "ANOTHER", "UNSAID"])
def test_every_gender_is_accepted(gender: str) -> None:
    assert StudentProfileUpdate(ageBand="18_22", gender=gender).gender == gender


@pytest.mark.parametrize(
    "body",
    [
        {"ageBand": "AGE_14_17", "gender": "WOMAN"},
        {"ageBand": "18_22", "gender": "PREFER_NOT_TO_SAY"},
        {"ageBand": "18_22"},
        {"ageBand": "18_22", "gender": "MAN", "age": 19},
    ],
)
def test_student_values_off_the_vocabulary_are_refused(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        StudentProfileUpdate(**body)


def test_an_artisan_names_one_to_twelve_crafts() -> None:
    assert ArtisanProfileUpdate(**ARTISAN_BODY).craftSlugs == ["kutch-ajrakh"]
    for slugs in ([], [f"craft-{n}" for n in range(13)]):
        with pytest.raises(ValidationError):
            ArtisanProfileUpdate(**{**ARTISAN_BODY, "craftSlugs": slugs})


@pytest.mark.parametrize("language", ["fr", "gu-IN", ""])
def test_the_spoken_language_is_an_answer_language(language: str) -> None:
    with pytest.raises(ValidationError):
        ArtisanProfileUpdate(**{**ARTISAN_BODY, "spokenLanguage": language})


def test_a_credit_mode_off_the_vocabulary_and_unknown_fields_are_refused() -> None:
    with pytest.raises(ValidationError):
        ArtisanProfileUpdate(**{**ARTISAN_BODY, "credit": {"mode": "NICKNAME"}})
    with pytest.raises(ValidationError):
        ArtisanProfileUpdate(**{**ARTISAN_BODY, "phone": "9876543210"})
    with pytest.raises(ValidationError):
        RecordingConsentRequest(noticeVersion="2026-11-18", language="gu", village="Dhamadka")


def test_listed_places_hold_every_coded_district_once_and_no_pending_one() -> None:
    states = load_listed_places()
    names = [state["name"] for state in states]
    assert names == sorted(names)
    assert names[0] == "Andaman and Nicobar Islands"
    gujarat = next(state for state in states if state["name"] == "Gujarat")
    assert gujarat["lgd"] == 24
    assert {"lgd": 449, "name": "Kachchh"} in gujarat["districts"]
    ladakh = next(state for state in states if state["name"] == "Ladakh")
    assert "Changthang" not in {district["name"] for district in ladakh["districts"]}
    lgds = [district["lgd"] for state in states for district in state["districts"]]
    assert len(lgds) == len(set(lgds)) == 786
