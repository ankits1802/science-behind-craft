import logging

import pytest

from app.geo.places import MASTER_LIST_LEVEL, practice_states, region_places
from app.geo.records import StateRecord
from app.schemas.region import MASTER_LIST_LABEL

from .golden_region import GI_JOURNAL, GI_JOURNAL_TITLE, GUJARAT, KACHCHH, VAV_THARAD, location

RAJASTHAN = StateRecord(8, "Rajasthan")
MADHYA_PRADESH = StateRecord(23, "Madhya Pradesh")
KNOWN = {state.name.casefold(): state for state in (GUJARAT, RAJASTHAN, MADHYA_PRADESH)}


def test_a_cited_district_location_is_a_district_place_and_hides_its_states_master_list_place() -> None:
    [place] = region_places([location()], [GUJARAT])
    assert (place.scope, place.district_lgd, place.basis_kind, place.source_id, place.basis_label) == (
        "DISTRICT",
        KACHCHH,
        "CRAFT_LOCATION",
        GI_JOURNAL,
        GI_JOURNAL_TITLE,
    )


def test_a_state_of_practice_without_a_district_place_cites_the_master_list() -> None:
    places = region_places([location()], [GUJARAT, RAJASTHAN])
    state = places[-1]
    assert (state.scope, state.state, state.place_label) == ("STATE", RAJASTHAN, "Rajasthan")
    assert (state.basis_kind, state.source_id, state.basis_label, state.level) == (
        "MASTER_LIST",
        None,
        MASTER_LIST_LABEL,
        MASTER_LIST_LEVEL,
    )


def test_a_location_without_a_visible_source_is_not_shown(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        places = region_places([location(source_id=None, source_title=None)], [GUJARAT])
    assert [(p.scope, p.basis_kind) for p in places] == [("STATE", "MASTER_LIST")]
    assert "location-kachchh has no visible source" in caplog.text


def test_a_point_outside_every_district_is_not_shown() -> None:
    assert region_places([location(precision="POINT", district_lgd=None, district_name=None)], []) == ()


def test_two_locations_in_one_district_are_one_place_cited_by_the_stronger() -> None:
    weak = location(id="a-weak", level="HYPOTHESIS", source_id="s-weak", source_title="Blog post")
    strong = location(id="b-strong", level="REVIEWED", source_id="s-strong", source_title="Gazetteer")
    [place] = region_places([weak, strong], [])
    assert (place.source_id, place.level) == ("s-strong", "REVIEWED")


def test_a_cited_state_location_is_a_state_place_unless_the_master_list_is_stronger() -> None:
    cited = location(
        id="state-mp", precision="STATE", state=MADHYA_PRADESH, district_lgd=None, place_label=None
    )
    [place] = region_places([cited], [MADHYA_PRADESH])
    assert (place.scope, place.basis_kind, place.place_label) == ("STATE", "MASTER_LIST", "Madhya Pradesh")
    verified = location(
        id="state-mp",
        precision="STATE",
        state=MADHYA_PRADESH,
        district_lgd=None,
        place_label="Bagh",
        level="VERIFIED",
    )
    [place] = region_places([verified], [MADHYA_PRADESH])
    assert (place.scope, place.basis_kind, place.source_id, place.place_label) == (
        "STATE",
        "CRAFT_LOCATION",
        GI_JOURNAL,
        "Bagh",
    )


def test_places_are_district_places_by_state_and_district_then_states_by_name() -> None:
    vav = location(id="vav", district_lgd=VAV_THARAD, district_name="Vav-Tharad", has_polygon=False)
    places = region_places([vav, location()], [RAJASTHAN, MADHYA_PRADESH, GUJARAT])
    assert [(p.scope, p.district_name or p.state.name) for p in places] == [
        ("DISTRICT", "Kachchh"),
        ("DISTRICT", "Vav-Tharad"),
        ("STATE", "Madhya Pradesh"),
        ("STATE", "Rajasthan"),
    ]


def test_a_district_place_without_a_label_is_named_for_its_district() -> None:
    [place] = region_places([location(place_label=None)], [])
    assert place.place_label == "Kachchh"


def test_states_of_practice_match_lgd_names_and_all_india_is_no_state(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        found = practice_states([" gujarat", "All India", "Gujarat", "Bombay State"], KNOWN)
    assert found == (GUJARAT,)
    assert "'Bombay State' is not an LGD state" in caplog.text
    assert "All India" not in caplog.text
