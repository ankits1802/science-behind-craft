import re
import uuid
from datetime import datetime

import pytest

from app.core.errors import InvalidInput
from app.schemas.media import MEDIA_FILE_NAME_PATTERN, MEDIA_S3_KEY_PATTERN
from app.services.naming import (
    MediaName,
    PlaceParts,
    content_disposition,
    generated_media_file_name,
    media_key,
)

from ..contracts.golden import golden_json

ROWS = golden_json("naming-golden.json")["generatedMedia"]


def media_name(row: dict) -> MediaName:
    return MediaName(
        kind=row["kind"],
        generated_at=datetime.fromisoformat(row["generatedAt"]),
        place=PlaceParts(**row["place"]),
        craft=row["craft"],
        stage_name=row["stageName"],
        stage_ordinal=row["stageOrdinal"],
    )


@pytest.mark.parametrize("row", ROWS, ids=[row["fileName"][:60] for row in ROWS])
def test_every_golden_media_name_is_reproduced(row: dict) -> None:
    name = generated_media_file_name(media_name(row))
    assert name == row["fileName"]
    assert re.fullmatch(MEDIA_FILE_NAME_PATTERN, name)
    assert len(name) <= 150


def test_the_golden_job_s_file_name_comes_from_the_helper() -> None:
    job = golden_json("media.job.golden.json")
    assert job["asset"]["fileName"] == ROWS[1]["fileName"]


def test_a_key_puts_the_owner_and_a_fresh_token_before_the_name() -> None:
    owner = uuid.UUID("66ceb1a0-fce2-5527-b3c8-c9c4507c60b9")
    token = uuid.UUID("8ff6abf0-198d-5196-8a87-3ef7dd5fc432")
    key = media_key(owner, ROWS[1]["fileName"], token=token)
    assert key == f"media/{owner}/8ff6abf0198d51968a873ef7dd5fc432/{ROWS[1]['fileName']}"
    assert re.fullmatch(MEDIA_S3_KEY_PATTERN, key)
    with pytest.raises(InvalidInput):
        media_key(owner, "nested/name.png")


def test_the_disposition_names_the_file_twice() -> None:
    assert content_disposition("KalaVigyan_A.png", inline=True) == (
        "inline; filename=\"KalaVigyan_A.png\"; filename*=UTF-8''KalaVigyan_A.png"
    )
    with pytest.raises(InvalidInput):
        content_disposition('bad"name.png', inline=True)


def test_a_stage_ordinal_must_fit_two_digits_and_times_carry_a_zone() -> None:
    row = ROWS[0]
    with pytest.raises(InvalidInput):
        generated_media_file_name(MediaName(**{**media_name(row).__dict__, "stage_ordinal": 100}))
    with pytest.raises(InvalidInput):
        generated_media_file_name(
            MediaName(
                **{**media_name(row).__dict__, "generated_at": datetime.fromisoformat("2026-11-16T14:30:00")}
            )
        )
