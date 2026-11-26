import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.routes import craft_media
from app.core.db import get_session
from app.core.errors import InvalidInput, NotConfigured
from app.main import create_app
from app.services.clip_stills import clip_still, still_args
from app.services.coded_clips import SharedClip
from app.services.naming import clip_still_key
from app.services.object_store import PresignedGet
from app.services.page_export_pictures import clip_still_src

CLIP = uuid.UUID("2d4f6a8c-0e1b-4c3d-9e5f-7a9b1c3d5e7f")
DIGEST = "e" * 64
LEAF = "KalaVigyan_Generated-Video_2026-11-21_0130_Bidar_Bidriware_Patina-Bath_Video_Step-04.mp4"
PAGE_KEY = f"media/craft/{DIGEST}/{LEAF}"
STILL_KEY = f"media/craft/{DIGEST}/KalaVigyan_Generated-Video_2026-11-21_0130_Bidar_Bidriware_Patina-Bath_Still_Step-04.jpg"
JPEG = b"\xff\xd8\xff\xe0still"
SHARED = SharedClip(
    asset_id=CLIP,
    page_key=PAGE_KEY,
    mime="video/mp4",
    model="veo-3.1-fast",
    made_at=datetime(2026, 11, 20, 20, 0, tzinfo=UTC),
    duration_seconds=8.0,
    claim_ids=frozenset(),
)


class Bucket:
    def __init__(self, stored: dict[str, bytes] | None = None) -> None:
        self.stored = dict(stored or {})
        self.signed: list[tuple[str, int]] = []
        self.puts: list[tuple[str, str]] = []

    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet:
        self.signed.append((key, seconds))
        return PresignedGet(url=f"https://bucket.example/{key}?X-Amz-Expires={seconds}", expires_at=now)

    async def get(self, key: str) -> bytes | None:
        return self.stored.get(key)

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        self.stored[key] = body
        self.puts.append((key, content_type))


def client(monkeypatch: pytest.MonkeyPatch, bucket: Bucket | None) -> TestClient:
    async def clip_of(session: object, asset_id: uuid.UUID) -> SharedClip | None:
        return SHARED if asset_id == CLIP else None

    async def released(session: object) -> None:
        return None

    monkeypatch.setattr(craft_media, "shared_clip", clip_of)
    monkeypatch.setattr(craft_media, "release_connection", released)
    monkeypatch.setattr(craft_media, "media_bucket", lambda: bucket)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: None
    return TestClient(app)


def test_a_shared_clip_is_signed_for_five_minutes_and_never_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    bucket = Bucket()
    response = client(monkeypatch, bucket).get(f"/api/crafts/media/{CLIP}/film")
    assert response.status_code == 200
    assert response.json()["url"] == f"https://bucket.example/{PAGE_KEY}?X-Amz-Expires=300"
    assert response.headers["cache-control"] == "no-store"
    assert bucket.signed == [(PAGE_KEY, 300)]


def test_a_clip_the_store_does_not_share_is_404_and_no_bucket_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    assert client(monkeypatch, Bucket()).get(f"/api/crafts/media/{uuid.uuid4()}/film").status_code == 404
    assert client(monkeypatch, None).get(f"/api/crafts/media/{CLIP}/film").status_code == 503
    assert client(monkeypatch, Bucket()).get(f"/api/crafts/media/{uuid.uuid4()}/still").status_code == 404


def test_the_still_is_served_at_the_address_the_export_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    kept = Bucket({STILL_KEY: JPEG})
    response = client(monkeypatch, kept).get(clip_still_src(CLIP))
    assert response.status_code == 200 and response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client(monkeypatch, Bucket()).get(clip_still_src(CLIP)).status_code == 404


def test_a_still_is_filed_beside_its_clip_and_only_a_video_copy_has_one() -> None:
    assert clip_still_key(PAGE_KEY) == STILL_KEY
    with pytest.raises(InvalidInput):
        clip_still_key(f"media/craft/{DIGEST}/KalaVigyan_Generated-Image_2026-11-21_0130_Image_Step-04.png")
    with pytest.raises(InvalidInput):
        clip_still_key(f"media/{uuid.uuid4()}/{uuid.uuid4().hex}/{LEAF}")


async def test_a_still_is_cut_once_at_the_clip_s_middle_and_kept() -> None:
    bucket = Bucket({PAGE_KEY: b"mp4 bytes"})
    asked: list[tuple[bytes, float]] = []

    async def cut(clip: bytes, at_seconds: float) -> bytes:
        asked.append((clip, at_seconds))
        return JPEG

    assert await clip_still(bucket, SHARED, cut=cut) == JPEG
    assert await clip_still(bucket, SHARED, cut=cut) == JPEG
    assert asked == [(b"mp4 bytes", 4.0)]
    assert bucket.puts == [(STILL_KEY, "image/jpeg")]


async def test_a_clip_with_no_copy_or_no_cut_has_no_still_and_nothing_is_kept() -> None:
    async def never(clip: bytes, at_seconds: float) -> bytes:
        raise AssertionError("nothing to cut")

    async def broken(clip: bytes, at_seconds: float) -> bytes:
        raise NotConfigured("ffmpeg", "ffmpeg is not installed on this machine")

    assert await clip_still(Bucket(), SHARED, cut=never) is None
    copied = Bucket({PAGE_KEY: b"mp4 bytes"})
    assert await clip_still(copied, SHARED, cut=broken) is None
    assert copied.puts == []


def test_ffmpeg_is_asked_for_one_jpeg_frame_at_the_time_given() -> None:
    args = still_args("/tmp/clip.mp4", 4.0)
    assert args[0] == "ffmpeg"
    assert args[args.index("-ss") + 1] == "4.000" and args[args.index("-i") + 1] == "/tmp/clip.mp4"
    assert args[args.index("-frames:v") + 1] == "1" and args[args.index("-c:v") + 1] == "mjpeg"
    assert args.index("-ss") < args.index("-i") and args[-1] == "pipe:1"
