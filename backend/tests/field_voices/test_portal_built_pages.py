from typing import Any

import pytest

from app.services.field_voices_feed import Live, parse_page
from app.services.field_voices_items import ImageItem, TranscriptItem
from app.services.field_voices_never_sent import forbidden_keys
from app.services.field_voices_records import recording_plan
from app.services.field_voices_screen import PortalScreen
from tests.field_voices.fixtures import DR, recorded

BUILT = ("portal-built-designer-transcripts", "portal-built-designer-images")


def parsed(name: str) -> Any:
    body = recorded(name)
    return parse_page(body, portal=DR, asked=(body["stream"], body["view"], body["cursor"]))


@pytest.mark.parametrize("name", BUILT)
def test_a_page_the_portals_own_builder_made_is_read_whole(name: str) -> None:
    body = recorded(name)
    assert forbidden_keys(body) == []
    page = parsed(name)
    assert page.changes and all(isinstance(change, Live) for change in page.changes)


@pytest.mark.parametrize("name", BUILT)
def test_kalavigyans_own_screen_finds_nothing_the_portal_missed(name: str) -> None:
    stream = recorded(name)["stream"]
    screen = PortalScreen()
    for change in parsed(name).changes:
        screen(stream, change.item.model_dump(mode="json", by_alias=True))
    assert screen.misses == 0


def test_the_portals_scrub_counts_arrive_as_a_list_of_the_legal_floors_kinds() -> None:
    item = parsed("portal-built-designer-transcripts").changes[0].item
    assert isinstance(item, TranscriptItem)
    assert item.scrubbing.version == 2
    assert [(entry.kind, entry.count) for entry in item.scrubbing.replaced] == [("EMAIL", 1), ("NUMBER", 1)]
    english = item.transcript.segments[1].english or ""
    assert "[number]" in english and "[email]" in english
    assert "Bagru" in item.transcript.segments[0].text and "Bagru" in english
    assert item.workshop is not None and item.workshop.title is not None and "Bagru" in item.workshop.title


def test_a_portal_built_stage_recording_quotes_its_designer_and_artisan() -> None:
    item = parsed("portal-built-designer-transcripts").changes[0].item
    plan = recording_plan(item, portal=DR)
    assert [(segment.role, segment.quotable) for segment in plan.segments] == [
        ("DESIGNER", True),
        ("ARTISAN", True),
    ]


def test_a_take_that_answers_an_identity_question_arrives_with_its_number_scrubbed() -> None:
    item = parsed("portal-built-designer-transcripts").changes[1].item
    assert isinstance(item, TranscriptItem)
    topic = item.topics[0]
    assert (topic.section_code, topic.question) == ("RESP", "Your phone number")
    text = item.transcript.segments[0].text
    assert "[number]" in text and "Bagru village" in text


def test_every_artisan_carries_the_credentials_the_portal_records() -> None:
    body = recorded("portal-built-designer-transcripts")
    for change in body["changes"]:
        artisans = [person for person in change["people"] if person["kind"] == "ARTISAN"]
        assert artisans and all(person["name"] and person["craft"] and person["area"] for person in artisans)
        assert all(person["craft"] is None for person in change["people"] if person["kind"] != "ARTISAN")
    item = parsed("portal-built-designer-transcripts").changes[0].item
    artisan = next(person for person in item.people if person.kind == "ARTISAN")
    assert (artisan.name, artisan.area.district if artisan.area else None) == ("Ravi Demo", "Jaipur")


def test_a_portal_built_prototype_photograph_credits_its_artisan_and_designer() -> None:
    item = parsed("portal-built-designer-images").changes[0].item
    assert isinstance(item, ImageItem)
    assert item.artisan_linked is False
    assert [(credit.person_id, credit.role) for credit in item.credits] == [
        ("dr-art-built", "ARTISAN"),
        ("dr-user-built", "DESIGNER"),
    ]
    assert item.belongs_to[0].field is not None and item.belongs_to[0].field.key == "prototypePhotos"


def test_a_portrait_filed_on_an_artisan_arrives_marked_and_an_event_photograph_does_not() -> None:
    prototype, portrait, event = (change.item for change in parsed("portal-built-designer-images").changes)
    assert isinstance(portrait, ImageItem) and isinstance(event, ImageItem)
    assert (portrait.artisan_linked, [placement.kind for placement in portrait.belongs_to]) == (
        True,
        ["ARTISAN"],
    )
    assert [(credit.person_id, credit.role) for credit in portrait.credits] == [("dr-art-built", "ARTISAN")]
    stage = event.belongs_to[0]
    assert event.artisan_linked is False
    assert stage.kind == "DESIGN_STAGE" and stage.field is not None and stage.field.key == "eventPhotos"
    assert prototype.id != portrait.id != event.id
