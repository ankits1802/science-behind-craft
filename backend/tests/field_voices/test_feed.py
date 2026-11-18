import hashlib
from collections.abc import Callable
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.services.field_voices_feed import (
    parse_index,
    parse_photographs_page,
    parse_quotes_page,
    snapshot_digest,
)
from app.services.field_voices_never_sent import forbidden_keys
from tests.field_voices.fixtures import AJRAKH, IMAGE_HOST, recorded
from tests.portal_sync.fixtures import edited

FR = "FIELD_REPOSITORY"
COPY = "ac43569be24108f18e631ec01bedaa001551fbfec80219bc5e7dad7a1a16ad91.jpg"


def quotes(payload: dict[str, Any], cursor: str | None = None) -> Any:
    return parse_quotes_page(payload, portal=FR, craft_slug=AJRAKH, cursor=cursor)


def photographs(payload: dict[str, Any], image_hosts: frozenset[str] = frozenset({IMAGE_HOST})) -> Any:
    return parse_photographs_page(payload, portal=FR, craft_slug=AJRAKH, cursor=None, image_hosts=image_hosts)


def test_the_recorded_index_parses_with_unknown_fields_ignored() -> None:
    index = parse_index(recorded("index"), portal=FR)
    assert [c.craft_slug for c in index.crafts] == ["Kutch-Ajrakh", "Dabu-Print"]
    ajrakh = index.crafts[0]
    assert (ajrakh.recordings, ajrakh.quotes, ajrakh.photographs) == (2, 3, 1)
    assert index.crafts[1].craft_code is None


def test_the_recorded_quote_pages_parse() -> None:
    first = quotes(recorded("quotes-1"))
    recording = first.recordings[0]
    assert first.next_cursor == "c2"
    assert recording.workshop is not None and recording.workshop.district == "Kachchh"
    assert recording.topics[0].question == "How do you prepare the mordant paste?"
    artisan = recording.artisans[0]
    assert (artisan.name, artisan.years_in_craft, artisan.consent.scope) == ("Asha Demo", 31, "ARTISAN")
    gujarati, hindi = recording.quotes
    assert (gujarati.language, gujarati.text_source, gujarati.english_source) == ("gu", "EDITED", "MACHINE")
    assert (hindi.english, hindi.english_source) == (None, None)
    second = quotes(recorded("quotes-2"), cursor="c2")
    unnamed = second.recordings[0].artisans[0]
    assert (unnamed.named, unnamed.name, unnamed.consent.basis) == (False, None, "OWNER_ATTESTATION")
    assert second.recordings[0].quotes[0].id == "turn-3.2"


def test_the_recorded_photograph_page_parses() -> None:
    photograph = photographs(recorded("photographs-1")).photographs[0]
    assert photograph.stage is not None and photograph.stage.step == "First resist printing"
    assert (photograph.image.width, photograph.image.height, photograph.image.mime_type) == (
        2400,
        1600,
        "image/jpeg",
    )
    assert photograph.consent.basis == "SIGNED_FORM"
    assert photograph.permission.licence is None


def test_another_schema_version_is_refused() -> None:
    with pytest.raises(InvalidInput, match="schemaVersion 2"):
        parse_index(edited(recorded("index"), lambda p: p.update(schemaVersion=2)), portal=FR)


def test_an_answer_from_the_other_portal_is_refused() -> None:
    with pytest.raises(InvalidInput, match="answered with a field voices index from DESIGNER"):
        parse_index(edited(recorded("index"), lambda p: p.update(portal="DESIGNER")), portal=FR)


@pytest.mark.parametrize(
    ("change", "cursor"),
    [(lambda p: p.update(craftSlug="Dabu-Print"), None), (lambda p: None, "c9")],
)
def test_a_page_for_another_craft_or_cursor_is_refused(change: Callable, cursor: str | None) -> None:
    with pytest.raises(InvalidInput, match="when asked for Kutch-Ajrakh"):
        quotes(edited(recorded("quotes-1"), change), cursor=cursor)


def put(path: tuple[Any, ...], key: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def change(payload: dict[str, Any]) -> None:
        target: Any = payload
        for step in path:
            target = target[step]
        target[key] = value

    return change


@pytest.mark.parametrize(
    ("page", "path", "key", "shown"),
    [
        ("quotes-1", ("recordings", 0, "artisans", 0), "phone", "recordings[0].artisans[0].phone"),
        ("quotes-1", ("recordings", 0, "artisans", 0), "dateOfBirth", "artisans[0].dateOfBirth"),
        ("quotes-1", ("recordings", 0, "artisans", 0), "age", "artisans[0].age"),
        ("quotes-1", ("recordings", 0, "artisans", 0, "consent"), "aadhaarLast4", "consent.aadhaarLast4"),
        ("quotes-1", ("recordings", 0, "workshop"), "address", "workshop.address"),
        ("quotes-1", ("recordings", 0), "pehchanCardNumber", "recordings[0].pehchanCardNumber"),
        ("photographs-1", ("photographs", 0), "latitude", "photographs[0].latitude"),
        ("photographs-1", ("photographs", 0, "artisans", 0), "email", "artisans[0].email"),
        ("photographs-1", ("photographs", 0, "artisans", 0), "gender", "artisans[0].gender"),
        ("photographs-1", ("photographs", 0), "lat", "photographs[0].lat"),
        ("photographs-1", ("photographs", 0), "lng", "photographs[0].lng"),
        ("photographs-1", ("photographs", 0), "lon", "photographs[0].lon"),
        ("photographs-1", ("photographs", 0), "long", "photographs[0].long"),
        ("photographs-1", ("photographs", 0), "gps", "photographs[0].gps"),
        ("photographs-1", ("photographs", 0), "coordinates", "photographs[0].coordinates"),
        ("photographs-1", ("photographs", 0), "geo", "photographs[0].geo"),
        ("photographs-1", ("photographs", 0), "geoLocation", "photographs[0].geoLocation"),
        ("photographs-1", ("photographs", 0), "altitude", "photographs[0].altitude"),
        ("photographs-1", ("photographs", 0), "accuracy", "photographs[0].accuracy"),
        ("photographs-1", ("photographs", 0, "workshop"), "subjectLatitude", "workshop.subjectLatitude"),
        ("quotes-1", ("recordings", 0, "workshop"), "village", "workshop.village"),
        ("quotes-1", ("recordings", 0, "workshop"), "placeName", "workshop.placeName"),
        ("quotes-1", ("recordings", 0, "workshop"), "place", "workshop.place"),
        ("quotes-1", ("recordings", 0, "artisans", 0), "place", "artisans[0].place"),
        ("quotes-1", ("recordings", 0, "artisans", 0), "locality", "artisans[0].locality"),
    ],
)
def test_a_field_that_is_never_sent_refuses_the_whole_answer(
    page: str, path: tuple[Any, ...], key: str, shown: str
) -> None:
    payload = edited(recorded(page), put(path, key, "x"))
    parse = quotes if page.startswith("quotes") else photographs
    with pytest.raises(InvalidInput, match="never sent") as caught:
        parse(payload)
    assert shown in str(caught.value)


def test_forbidden_keys_spares_words_that_only_contain_a_forbidden_one() -> None:
    payload = {
        "language": "gu",
        "stage": {},
        "translation": "x",
        "geology": "x",
        "longest": "x",
        "placement": "x",
        "image": {"mimeType": "x"},
        "a": [{"phoneNumber": 1}],
    }
    assert forbidden_keys(payload) == ["a[0].phoneNumber"]


RECORDING = ("recordings", 0)
MEDIA_KEY_URL = (
    f"https://{IMAGE_HOST}/media/user-7/0f0e/FieldRepository_Workshop_2026-03-13_Ajrakhpur-Kachchh_Photo.jpg"
)
NAMED_FILE_URL = (
    f"https://{IMAGE_HOST}/field-voices/{COPY}"
    "?response-content-disposition=inline%3B%20filename%3D%22Ajrakhpur-Kachchh_Asha-Demo_Photo.jpg%22"
)
ARTISAN = ("recordings", 0, "artisans", 0)
QUOTE = ("recordings", 0, "quotes", 0)
PHOTOGRAPH = ("photographs", 0)


def credit_a_silent_artisan(payload: dict[str, Any]) -> None:
    artisans = payload["recordings"][0]["artisans"]
    artisans.append({**artisans[0], "id": "art-3"})


@pytest.mark.parametrize(
    ("page", "change", "problem"),
    [
        ("quotes-1", put(QUOTE, "artisanId", "art-9"), "does not credit"),
        ("quotes-1", credit_a_silent_artisan, "who is not quoted"),
        ("quotes-1", put(ARTISAN, "name", None), "named is true"),
        ("quotes-2", put((*RECORDING, "artisans", 0), "name", "Somebody"), "named is true"),
        ("quotes-2", put((*RECORDING, "artisans", 0), "localName", "x"), "unnamed and carries"),
        ("quotes-1", put((*RECORDING, "quotes", 1), "english", "Iron turns it black."), "come together"),
        ("quotes-1", put(QUOTE, "endMs", 700000), "ends before it starts"),
        ("quotes-1", put(QUOTE, "endMs", 1900000), "past its end"),
        ("quotes-1", put(QUOTE, "language", "Gujarati"), "language"),
        ("quotes-1", put((*ARTISAN, "consent"), "basis", "IMPLIED"), "basis"),
        ("quotes-1", put(RECORDING, "recordedAt", "2026-03-14T10:22:00"), "recordedAt"),
        ("quotes-1", put(ARTISAN, "yearsInCraft", 120), "yearsInCraft"),
        ("quotes-1", put(RECORDING, "revision", "two words"), "revision"),
        ("photographs-1", put((*PHOTOGRAPH, "consent"), "basis", "OWNER_ATTESTATION"), "own consent"),
        ("photographs-1", put((*PHOTOGRAPH, "consent"), "scope", "ARTISAN"), "own consent"),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "expiresAt", "2026-11-18T02:20:03Z"), "15 minutes"),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "expiresAt", "2026-11-18T01:59:00Z"), "15 minutes"),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "url", "http://media.example.com/a.jpg"), "url"),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "width", 4000), "width"),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "mimeType", "image/heic"), "mimeType"),
        (
            "photographs-1",
            put((*PHOTOGRAPH, "image"), "mimeType", "image/png"),
            f"/field-voices/{COPY[:-3]}png",
        ),
        ("photographs-1", put((*PHOTOGRAPH, "image"), "url", MEDIA_KEY_URL), "nothing else"),
        (
            "photographs-1",
            put((*PHOTOGRAPH, "image"), "url", f"https://{IMAGE_HOST}:8443/field-voices/{COPY}"),
            "nothing else",
        ),
        (
            "photographs-1",
            put((*PHOTOGRAPH, "image"), "url", NAMED_FILE_URL),
            "names a file other than its copy",
        ),
    ],
)
def test_a_page_that_breaks_the_contract_is_refused(
    page: str, change: Callable[[dict[str, Any]], None], problem: str
) -> None:
    payload = edited(recorded(page), change)
    with pytest.raises(InvalidInput, match="breaks the contract") as caught:
        if page.startswith("quotes"):
            quotes(payload, cursor=payload["cursor"])
        else:
            photographs(payload)
    assert problem in str(caught.value)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda p: p["crafts"].append(dict(p["crafts"][0])), "appears twice"),
        (lambda p: p["crafts"][0].update(recordings=0, photographs=0), "nothing to publish"),
        (lambda p: p["crafts"][0].update(quotes=1), "fewer quotes than recordings"),
        (lambda p: p["crafts"][0].update(digest="ABC"), "digest"),
        (lambda p: p["crafts"][0].update(craftSlug="../crafts"), "craftSlug"),
    ],
)
def test_an_index_that_breaks_the_contract_is_refused(change: Callable, problem: str) -> None:
    with pytest.raises(InvalidInput, match="breaks the contract") as caught:
        parse_index(edited(recorded("index"), change), portal=FR)
    assert problem in str(caught.value)


def test_the_snapshot_digest_is_the_sha256_of_the_sorted_lines() -> None:
    recordings = quotes(recorded("quotes-1")).recordings + quotes(recorded("quotes-2"), "c2").recordings
    pictures = photographs(recorded("photographs-1")).photographs
    lines = (
        "P photo-1 7b44d54b1fb4b16a9fd145c5fc893613\n"
        "R rec-1 91bdd4e889f5d9736c6c2fbd944dfd73\n"
        "R rec-2 f934cb90d32e02ebeebf08105f111c34\n"
    )
    expected = hashlib.sha256(lines.encode("utf-8")).hexdigest()
    assert snapshot_digest(recordings, pictures) == expected
    assert recorded("index")["crafts"][0]["digest"] == expected


def test_an_image_on_a_host_that_is_not_listed_is_refused() -> None:
    with pytest.raises(InvalidInput, match="photo-1 is served from a host") as caught:
        photographs(recorded("photographs-1"), image_hosts=frozenset({"other.example.com"}))
    assert IMAGE_HOST not in str(caught.value)


def test_a_workshop_without_a_title_parses() -> None:
    payload = edited(recorded("quotes-1"), put((*RECORDING, "workshop"), "title", None))
    workshop = quotes(payload).recordings[0].workshop
    assert workshop is not None and (workshop.title, workshop.district) == (None, "Kachchh")
