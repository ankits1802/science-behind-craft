import hashlib
from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from app.core.errors import InvalidInput
from app.services.field_voices_feed import Live, parse_page
from app.services.field_voices_images import ImageCopier
from app.services.field_voices_items import ImageItem
from app.services.malware_scan import MalwareFound, ScannerDown
from tests.field_voices.fixtures import FR, FR_HOST, recorded, resigned
from tests.upload_scanners import EICAR, EICAR_SIGNATURE, ScriptedScanner

GPS_IFD = 0x8825
ARTIST = 0x013B


class FakeStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.authorised: list[str] = []

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        self.objects[key] = (body, content_type)


def tagged_jpeg() -> bytes:
    exif = Image.Exif()
    exif[ARTIST] = "Asha Demo 9825012345"
    exif[GPS_IFD] = {1: "N", 2: (23.0, 15.0, 0.0)}
    out = BytesIO()
    Image.new("RGB", (40, 30), (180, 40, 30)).save(out, format="JPEG", exif=exif)
    return out.getvalue()


def portal_image(body: bytes) -> ImageItem:
    page = recorded("field-images-all-1")
    image = page["changes"][0]["image"]
    image.update(width=40, height=30, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    image["url"] = f"https://{FR_HOST}/field-voices/{image['sha256']}.jpg?X-Amz-Expires=900"
    resigned(page["changes"][0])
    change = parse_page(page, portal=FR, asked=("images", "all", None)).changes[0]
    assert isinstance(change, Live) and isinstance(change.item, ImageItem)
    return change.item


def copier(store: Any, body: bytes, seen: list[httpx.Request]) -> ImageCopier:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=body)

    return ImageCopier(store, image_hosts=frozenset({FR_HOST}), transport=httpx.MockTransport(handler))


async def test_the_copy_drops_every_tag_and_is_filed_under_its_own_hash() -> None:
    body = tagged_jpeg()
    store, seen = FakeStore(), []
    stored = await copier(store, body, seen).copy(portal_image(body))
    data, content_type = store.objects[stored.key]
    assert content_type == "image/jpeg"
    with Image.open(BytesIO(data)) as opened:
        assert not opened.getexif()
        assert "icc_profile" not in opened.info
    assert stored.sha256 == hashlib.sha256(data).hexdigest() != stored.portal_sha256
    assert stored.key == (
        f"media/field-voices/{stored.sha256}/KalaVigyan_Field-Image_2026-03-14_1140_Kachchh_Ajrakh-Print-Of-Kutch_Photo.jpg"
    )
    assert "authorization" not in seen[0].headers
    assert "x-cross-portal-nonce" not in seen[0].headers


async def test_a_body_that_is_not_the_announced_image_is_refused() -> None:
    body = tagged_jpeg()
    item = portal_image(body)
    with pytest.raises(InvalidInput, match=r"SHA-256|bytes"):
        await copier(FakeStore(), body + b"tail", []).copy(item)


async def test_a_copy_is_stored_once_for_the_same_picture() -> None:
    body = tagged_jpeg()
    store: Any = FakeStore()
    first = await copier(store, body, []).copy(portal_image(body))
    second = await copier(store, body, []).copy(portal_image(body))
    assert first.key == second.key and len(store.objects) == 1


async def test_a_portal_picture_is_scanned_whole_before_it_is_decoded(
    upload_scanner: ScriptedScanner,
) -> None:
    body = tagged_jpeg()
    store: Any = FakeStore()
    await copier(store, body, []).copy(portal_image(body))
    assert upload_scanner.scanned == [body] and len(store.objects) == 1


async def test_a_portal_picture_carrying_the_eicar_test_file_is_refused_and_nothing_is_stored() -> None:
    body = tagged_jpeg() + EICAR.encode("ascii")
    store: Any = FakeStore()
    with pytest.raises(MalwareFound, match=EICAR_SIGNATURE):
        await copier(store, body, []).copy(portal_image(body))
    assert store.objects == {}


async def test_with_the_scanner_down_no_portal_picture_is_decoded_or_stored(
    upload_scanner: ScriptedScanner,
) -> None:
    upload_scanner.down = True
    body = tagged_jpeg()
    store: Any = FakeStore()
    with pytest.raises(ScannerDown, match="not answering"):
        await copier(store, body, []).copy(portal_image(body))
    assert store.objects == {}
