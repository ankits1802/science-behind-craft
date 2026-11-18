import copy
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.services.field_voices_feed import Gone, Live, item_revision, parse_page, parse_state, stream_digest
from app.services.field_voices_items import ImageItem, TranscriptItem
from app.services.field_voices_never_sent import forbidden_keys
from tests.field_voices.fixtures import DR, FR, recorded, reference_digest, reference_revision, resigned


def page(name: str, portal: str = FR, payload: dict[str, Any] | None = None) -> Any:
    body = payload if payload is not None else recorded(name)
    return parse_page(body, portal=portal, asked=(body["stream"], body["view"], body["cursor"]))


def test_both_portals_answer_the_same_state_shape() -> None:
    for portal, prefix in ((FR, "field"), (DR, "designer")):
        state = parse_state(recorded(f"{prefix}-state"), portal=portal)
        assert state.portal == portal
        assert state.stream("transcripts").enabled and state.stream("images").enabled


def test_the_state_digest_is_the_live_set_of_the_recorded_pages() -> None:
    state = parse_state(recorded("field-state"), portal=FR)
    live = [
        (change["id"], change["revision"])
        for name in ("field-transcripts-all-1", "field-transcripts-all-2")
        for change in recorded(name)["changes"]
        if change["state"] == "LIVE"
    ]
    assert state.stream("transcripts").digest == reference_digest(live)
    assert stream_digest(live) == reference_digest(live)


def test_a_field_repository_transcript_page_parses_with_unknown_fields_ignored() -> None:
    first = page("field-transcripts-all-1")
    live, gone = first.changes
    assert isinstance(live, Live) and isinstance(live.item, TranscriptItem)
    item = live.item
    assert (first.next_cursor, first.has_more) == ("fr-t-2", True)
    assert [segment.speaker_key for segment in item.transcript.segments] == [
        "speaker_1",
        "speaker_0",
        "speaker_0",
        "speaker_2",
    ]
    assert item.transcript.segments[1].scrubbed == ("NUMBER",)
    assert item.people[0].merged_ids == ("fr-art-old",)
    assert isinstance(gone, Gone) and (gone.reason, gone.successor_id) == ("DELETED", None)


def test_a_designer_portal_stage_recording_and_prototype_image_parse() -> None:
    transcripts = page("designer-transcripts-all-1", DR)
    recording = transcripts.changes[0]
    assert isinstance(recording, Live) and isinstance(recording.item, TranscriptItem)
    assert recording.item.stage is not None and recording.item.stage.field == "audioNarration"
    replaced = transcripts.changes[1]
    assert isinstance(replaced, Gone) and (replaced.reason, replaced.successor_id) == (
        "REPLACED",
        "dr-media-1",
    )
    image = page("designer-images-all-1", DR).changes[0]
    assert isinstance(image, Live) and isinstance(image.item, ImageItem)
    placement = image.item.belongs_to[0]
    assert (placement.kind, placement.prototype_id) == ("DESIGN_STAGE", "dr-row-5")
    assert [credit.role for credit in image.item.credits] == ["ARTISAN", "DESIGNER"]


def test_the_revision_is_the_contracts_hash_without_the_link() -> None:
    for name in ("field-transcripts-all-1", "field-images-all-1", "designer-images-all-1"):
        for change in recorded(name)["changes"]:
            if change["state"] == "LIVE":
                assert item_revision(change) == reference_revision(change) == change["revision"]
    image = recorded("field-images-all-1")["changes"][0]
    moved = copy.deepcopy(image)
    moved["image"]["url"] = moved["image"]["url"].replace("abc", "zzz")
    moved["image"]["expiresAt"] = "2026-11-18T02:14:00Z"
    assert item_revision(moved) == image["revision"]


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("people", "phone"),
        ("people", "mobileNumber"),
        ("people", "aadhaarLast4"),
        ("people", "dateOfBirth"),
        ("people", "emailAddress"),
        ("area", "village"),
        ("area", "pincode"),
        ("area", "lat"),
        ("workshop", "venue"),
        ("workshop", "clusterName"),
        ("people", "bankAccount"),
        ("people", "signatureMediaId"),
        ("people", "empanelmentNo"),
        ("people", "otp"),
        ("workshop", "city"),
    ],
)
def test_a_never_sent_key_anywhere_refuses_the_page(path: str, key: str) -> None:
    body = recorded("field-transcripts-all-1")
    holder = body["changes"][0][path]
    (holder[0] if isinstance(holder, list) else holder)[key] = "x"
    with pytest.raises(InvalidInput, match="never sent"):
        page("", payload=body)


def test_scrub_counts_are_a_list_because_their_kinds_are_never_sent_keys() -> None:
    body = recorded("field-transcripts-all-1")
    assert forbidden_keys(body) == []
    assert body["changes"][0]["scrubbing"]["replaced"] == [
        {"kind": "EMAIL", "count": 0},
        {"kind": "NUMBER", "count": 1},
        {"kind": "PLACE", "count": 0},
    ]
    body["changes"][0]["scrubbing"]["replaced"] = {"EMAIL": 0, "NUMBER": 1, "PLACE": 0}
    assert sorted(forbidden_keys(body)) == [
        "changes[0].scrubbing.replaced.EMAIL",
        "changes[0].scrubbing.replaced.PLACE",
    ]
    with pytest.raises(InvalidInput, match="never sent"):
        page("", payload=body)


def test_a_scrub_kind_counted_twice_refuses_the_page() -> None:
    body = recorded("field-transcripts-all-1")
    body["changes"][0]["scrubbing"]["replaced"].append({"kind": "NUMBER", "count": 1})
    resigned(body["changes"][0])
    with pytest.raises(InvalidInput, match="scrub kind"):
        page("", payload=body)


def test_a_live_item_whose_revision_differs_is_refused() -> None:
    body = recorded("field-transcripts-all-1")
    body["changes"][0]["transcript"]["segments"][1]["text"] = "changed after signing"
    with pytest.raises(InvalidInput, match="does not match its revision"):
        page("", payload=body)


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(stream="images"),
        lambda b: b.update(cursor="fr-t-9"),
        lambda b: b.update(view="gone"),
        lambda b: b.update(portal=DR),
    ],
)
def test_a_page_that_answers_another_request_is_refused(change: Any) -> None:
    body = recorded("field-transcripts-all-1")
    change(body)
    with pytest.raises(InvalidInput):
        parse_page(body, portal=FR, asked=("transcripts", "all", None))


def test_changes_out_of_order_are_refused() -> None:
    body = recorded("field-transcripts-all-1")
    body["changes"].reverse()
    with pytest.raises(InvalidInput, match="out of order"):
        page("", payload=body)


def test_the_gone_view_carries_only_tombstones() -> None:
    body = recorded("field-transcripts-all-1")
    body.update(view="gone")
    with pytest.raises(InvalidInput, match="live item"):
        parse_page(body, portal=FR, asked=("transcripts", "gone", None))


@pytest.mark.parametrize(
    "change",
    [
        lambda g: g.update(transcript={"segments": []}),
        lambda g: g.update(reason="REPLACED"),
        lambda g: g.update(successorId="fr-media-9"),
        lambda g: g.update(reason=None),
    ],
)
def test_a_tombstone_carries_its_reason_and_nothing_else(change: Any) -> None:
    body = recorded("field-transcripts-gone-1")
    change(body["changes"][0])
    with pytest.raises(InvalidInput):
        page("", payload=body)


def test_a_speaker_mapped_to_an_unlisted_person_is_refused() -> None:
    body = recorded("field-transcripts-all-1")
    body["changes"][0]["speakers"][0]["personId"] = "fr-art-unknown"
    resigned(body["changes"][0])
    with pytest.raises(InvalidInput, match="does not list"):
        page("", payload=body)


@pytest.mark.parametrize(
    "url",
    [
        "https://fieldrepo.example.com/media/u1/x/Asha_Demo.jpg",
        "https://fieldrepo.example.com:8443/field-voices/{leaf}",
        "https://fieldrepo.example.com/field-voices/{leaf}?response-content-disposition=inline%3B%20filename%3DAsha.jpg",
    ],
)
def test_an_image_link_naming_anything_but_the_neutral_copy_is_refused(url: str) -> None:
    body = recorded("field-images-all-1")
    image = body["changes"][0]["image"]
    image["url"] = url.format(leaf=f"{image['sha256']}.jpg")
    with pytest.raises(InvalidInput):
        page("", payload=body)


def test_an_image_link_living_past_fifteen_minutes_is_refused() -> None:
    body = recorded("field-images-all-1")
    body["changes"][0]["image"]["expiresAt"] = "2026-11-18T03:00:00Z"
    with pytest.raises(InvalidInput, match="15 minutes"):
        page("", payload=body)


def test_an_empty_page_keeps_the_cursor_it_was_asked_for() -> None:
    empty = page("field-images-gone-1")
    assert (empty.changes, empty.next_cursor, empty.has_more) == ((), None, False)
    body = recorded("field-images-gone-1")
    body["nextCursor"] = "fr-i-9"
    with pytest.raises(InvalidInput, match="moved"):
        page("", payload=body)


def test_another_schema_version_is_refused() -> None:
    body = recorded("field-state")
    body["schemaVersion"] = 1
    with pytest.raises(InvalidInput, match="schemaVersion"):
        parse_state(body, portal=FR)
