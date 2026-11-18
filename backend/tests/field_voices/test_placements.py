from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.services.field_voices_feed import Live, parse_page
from app.services.field_voices_items import ImageItem, TranscriptItem
from app.services.field_voices_photos import photo_groups
from app.services.field_voices_screen import PortalScreen
from tests.field_voices.fixtures import DR, FR, recorded, resigned


def parsed(body: dict[str, Any], portal: str = DR) -> Any:
    return parse_page(body, portal=portal, asked=(body["stream"], body["view"], body["cursor"]))


def stage_image(stage: str, entity: str, field: str) -> dict[str, Any]:
    body = recorded("designer-images-all-1")
    placement = body["changes"][0]["belongsTo"][0]
    placement["stage"]["key"], placement["entity"]["key"], placement["field"]["key"] = stage, entity, field
    resigned(body["changes"][0])
    return body


def stage_recording(stage: str, entity: str, field: str) -> dict[str, Any]:
    body = recorded("designer-transcripts-all-1")
    shown = body["changes"][0]["stage"]
    shown["key"], shown["entity"], shown["field"] = stage, entity, field
    resigned(body["changes"][0])
    return body


def test_a_stage_image_and_a_stage_recording_are_read() -> None:
    for name in ("designer-images-all-1", "designer-transcripts-all-1"):
        assert isinstance(parsed(recorded(name)).changes[0], Live)


@pytest.mark.parametrize(
    ("stage", "entity", "field"),
    [
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "participant", "photo"),
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "eventPhotos"),
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "openingPhotos"),
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "designerPhoto"),
        ("WORKSHOP_SETUP", "workshopSetup", "coverPhoto"),
        ("DESIGN_BRIEF", "designBrief", "moodBoard"),
        ("MARKET_SURVEY_CAPTURE", "surveySummary", "marketPhotos"),
        ("INSPECTION_CLOSING", "closing", "closingPhotos"),
        ("REPORT_GENERATION", "reportSettings", "logo"),
        ("PROTOTYPE_DEVELOPMENT", "_custom", "_custom"),
    ],
)
def test_an_image_filed_in_any_stage_field_is_read(stage: str, entity: str, field: str) -> None:
    assert isinstance(parsed(stage_image(stage, entity, field)).changes[0], Live)


@pytest.mark.parametrize(
    ("stage", "entity", "field"),
    [
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "designerSignature"),
        ("INSPECTION_CLOSING", "certificate", "signatureImage"),
    ],
)
def test_a_signature_field_refuses_the_page(stage: str, entity: str, field: str) -> None:
    with pytest.raises(InvalidInput, match="never sent"):
        parsed(stage_image(stage, entity, field))


@pytest.mark.parametrize(
    ("stage", "entity", "field"),
    [
        ("MARKET_SURVEY_CAPTURE", "surveyResponse", "voiceNote"),
        ("INSPECTION_CLOSING", "closing", "summaryVideo"),
        ("PROTOTYPE_DEVELOPMENT", "_custom", "_custom"),
    ],
)
def test_stage_media_in_any_field_is_read(stage: str, entity: str, field: str) -> None:
    assert isinstance(parsed(stage_recording(stage, entity, field)).changes[0], Live)


@pytest.mark.parametrize(
    "caption",
    [
        "Aadhaar card of the artisan",
        "Signature page",
        "Voter ID",
        "Consent form",
        "PAN card",
        "Driving licence",
        "Pehchan card",
        "Bank passbook first page",
        "Cancelled cheque",
        "UPI QR code",
        "Thumb impression on the register",
    ],
)
def test_an_image_captioned_as_an_identity_document_or_bank_detail_refuses_the_page(caption: str) -> None:
    body = recorded("designer-images-all-1")
    body["changes"][0]["caption"] = caption
    resigned(body["changes"][0])
    with pytest.raises(InvalidInput, match="identity document"):
        parsed(body)


@pytest.mark.parametrize(
    "caption",
    ["Brand identity board", "Preserving craft identity and authenticity", "Bandhani on a valid card stock"],
)
def test_an_ordinary_caption_that_mentions_identity_or_a_card_is_read(caption: str) -> None:
    body = recorded("designer-images-all-1")
    body["changes"][0]["caption"] = caption
    resigned(body["changes"][0])
    assert isinstance(parsed(body).changes[0], Live)


FILED = [
    {"kind": "ARTISAN", "id": "dr-art-9", "name": "Ravi Demo", "localName": None},
    {"kind": "DESIGNER", "id": "dr-user-9", "name": "Meera Demo"},
    {"kind": "SESSION", "id": "dr-ses-9", "name": "Sitting at Bagru"},
    {"kind": "WORKSHOP", "id": "dr-ws-9", "name": "Bagru documentation visit"},
    {"kind": "DESIGN_WORKSHOP", "id": "dr-dw-9", "name": None},
]


def filed_image(placement: dict[str, Any], *, linked: bool) -> dict[str, Any]:
    body = recorded("designer-images-all-1")
    change = body["changes"][0]
    change["belongsTo"] = [placement]
    change["artisanLinked"] = linked
    resigned(change)
    return body


@pytest.mark.parametrize("placement", FILED, ids=lambda p: p["kind"])
def test_an_image_filed_on_a_person_a_session_or_a_workshop_is_read_with_its_marker(
    placement: dict[str, Any],
) -> None:
    linked = placement["kind"] in ("ARTISAN", "SESSION")
    item = parsed(filed_image(placement, linked=linked)).changes[0].item
    assert isinstance(item, ImageItem)
    assert item.artisan_linked is linked
    assert item.belongs_to[0].kind == placement["kind"]


def test_an_image_without_the_artisan_marker_refuses_the_page() -> None:
    body = recorded("designer-images-all-1")
    del body["changes"][0]["artisanLinked"]
    resigned(body["changes"][0])
    with pytest.raises(InvalidInput):
        parsed(body)


def test_filed_placements_group_under_a_person_a_session_or_a_workshop() -> None:
    body = filed_image(FILED[0], linked=True)
    change = body["changes"][0]
    change["belongsTo"] = FILED
    resigned(change)
    item = parsed(body).changes[0].item
    groups = [(group.kind, group.key, group.label) for group in photo_groups(item.belongs_to)]
    assert groups == [
        ("PERSON", "person:dr-art-9", "Ravi Demo"),
        ("PERSON", "person:dr-user-9", "Meera Demo"),
        ("SESSION", "session:dr-ses-9", "Sitting at Bagru"),
        ("WORKSHOP", "workshop:dr-ws-9", "Bagru documentation visit"),
        ("WORKSHOP", "workshop:dr-dw-9", "The design workshop"),
    ]


def test_village_names_and_identity_question_takes_are_read_and_not_counted_as_misses() -> None:
    body = recorded("field-transcripts-all-1")
    change = body["changes"][0]
    change["session"]["title"] = "Interview_2026-03-14_Dhamadka-Kachchh_Ajrakh"
    change["topics"] = [
        {
            "sectionId": "fr-sec-resp",
            "sectionCode": "RESP",
            "sectionTitle": "Respondent Information",
            "questionId": "fr-qn-8",
            "questionCode": "RESP-Q08",
            "question": "Contact Number",
        }
    ]
    segment = change["transcript"]["segments"][0]
    segment["text"] = "I live in Dhamadka village near Bhuj; my number is [number]."
    segment["english"] = segment["text"]
    resigned(change)
    item = parsed(body, FR).changes[0].item
    assert isinstance(item, TranscriptItem)
    screen = PortalScreen()
    shown = screen("transcripts", item.model_dump(mode="json", by_alias=True))
    assert shown["session"]["title"] == "Interview_2026-03-14_Dhamadka-Kachchh_Ajrakh"
    assert shown["topics"][0]["question"] == "Contact Number"
    assert (
        shown["transcript"]["segments"][0]["text"]
        == "I live in Dhamadka village near Bhuj; my number is [number]."
    )
    assert screen.misses == 0
