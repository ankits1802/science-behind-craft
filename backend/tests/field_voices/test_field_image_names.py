from datetime import datetime
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.services.naming import PlaceParts, field_voice_file_name, field_voice_key
from tests.contracts.golden import golden_json

ROWS = golden_json("naming-golden.json")["fieldVoiceFiles"]


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["fileName"])
def test_field_images_follow_the_naming_golden(row: dict[str, Any]) -> None:
    taken = datetime.fromisoformat(row["takenAt"]) if row["takenAt"] else None
    place = PlaceParts(district=row["district"], state=row["state"])
    leaf = field_voice_file_name(taken_at=taken, place=place, craft=row["craft"], ext=row["ext"])
    assert leaf == row["fileName"]
    assert field_voice_key(row["sha256"], leaf) == row["key"]


def test_a_field_image_name_never_carries_a_locality() -> None:
    place = PlaceParts(locality="Ajrakhpur", district="Kachchh", state="Gujarat")
    leaf = field_voice_file_name(taken_at=None, place=place, craft="Ajrakh Print of Kutch", ext="jpg")
    assert "Ajrakhpur" not in leaf


@pytest.mark.parametrize("ext", ["webp", "gif", ""])
def test_a_field_image_is_stored_as_jpeg_or_png_only(ext: str) -> None:
    with pytest.raises(InvalidInput):
        field_voice_file_name(taken_at=None, place=PlaceParts(), craft="Craft", ext=ext)


def test_a_field_image_key_is_filed_under_kalavigyans_copy_hash() -> None:
    with pytest.raises(InvalidInput):
        field_voice_key("not-a-hash", "KalaVigyan_Field-Image_Photo.jpg")
    with pytest.raises(InvalidInput):
        field_voice_key("0" * 64, "nested/leaf.jpg")
