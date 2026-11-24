from app.models import ImageContribution, OpenPicture
from app.models.enums import DECLARED_ORIGINS, IMAGE_ORIGINS, OPEN_PICTURE_SITES

from .migration_scripts import migration

STEP = migration("0102_open_pictures")


def test_it_follows_the_oauth_code_token_version() -> None:
    assert (STEP.revision, STEP.down_revision) == ("0102_open_pictures", "0101_oauth_code_token_version")


def test_it_adds_the_open_licence_origin_to_the_origins_a_person_declares() -> None:
    assert STEP.ORIGINS_BEFORE == DECLARED_ORIGINS == ("PHOTOGRAPH", "DRAWING", "AI_GENERATED")
    assert STEP.ORIGINS == IMAGE_ORIGINS == (*DECLARED_ORIGINS, "OPEN_LICENCE")
    assert STEP.SITES == OPEN_PICTURE_SITES == ("COMMONS", "OPENVERSE", "FLICKR")


def test_the_release_before_reads_and_writes_a_picture_without_the_new_table() -> None:
    assert ImageContribution.__table__.columns["origin"].nullable is False
    columns = OpenPicture.__table__.columns
    assert [column.name for column in columns if column.primary_key] == ["contributionId"]
    assert {column.name for column in columns if column.nullable} == {"licenceUrl", "width", "height"}
