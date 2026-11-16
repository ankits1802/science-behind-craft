import pytest

from app.core.errors import InvalidInput
from app.services.portal_craft_feed import parse_feed
from tests.portal_sync.fixtures import designer_payload, edited


def test_a_contract_feed_parses_with_unknown_fields_ignored() -> None:
    feed = parse_feed(designer_payload(), portal="DESIGNER")
    assert feed.portal == "DESIGNER"
    assert [c.slug for c in feed.crafts] == ["Kutch-Ajrakh", "Dabu-Print", "Dabu-Printing", "Sanjhi"]
    assert feed.crafts[2].merged_into_id == "d2"
    assert feed.categories[1].sub_categories[0].slug == "Paper-Cutting"
    assert feed.spellings[0].craft_code == "dabu"


def test_another_schema_version_is_refused() -> None:
    payload = edited(designer_payload(), lambda p: p.update(schemaVersion=2))
    with pytest.raises(InvalidInput, match="schemaVersion 2"):
        parse_feed(payload, portal="DESIGNER")


def test_a_feed_from_the_other_portal_is_refused() -> None:
    with pytest.raises(InvalidInput, match="answered with a feed from DESIGNER"):
        parse_feed(designer_payload(), portal="FIELD_REPOSITORY")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p["crafts"][2].update(mergedIntoId=None), "MERGED and mergedIntoId"),
        (lambda p: p["crafts"][0].update(mergedIntoId="d2"), "MERGED and mergedIntoId"),
        (lambda p: p["crafts"][1].update(subCategoryId="nowhere"), "subCategoryId 'nowhere'"),
        (lambda p: p["crafts"][1].update(craftCode="nocode"), "craftCode 'nocode'"),
        (lambda p: p["crafts"][2].update(mergedIntoId="d9"), "mergedIntoId 'd9'"),
        (lambda p: p["crafts"][3].update(slug="Dabu-Print"), "craft slug 'Dabu-Print' appears twice"),
        (lambda p: p["spellings"][0].update(craftCode="nocode"), "craftCode 'nocode'"),
        (lambda p: p["crafts"][0].update(status="RETIRED"), "status"),
    ],
)
def test_a_feed_that_breaks_its_own_references_is_refused(change, message: str) -> None:
    with pytest.raises(InvalidInput, match=message):
        parse_feed(edited(designer_payload(), change), portal="DESIGNER")


def test_a_craft_merged_into_itself_is_refused() -> None:
    payload = edited(designer_payload(), lambda p: p["crafts"][2].update(mergedIntoId="d3"))
    with pytest.raises(InvalidInput, match="merged into itself"):
        parse_feed(payload, portal="DESIGNER")


def test_a_non_object_answer_is_refused() -> None:
    with pytest.raises(InvalidInput, match="not a JSON object"):
        parse_feed([1, 2], portal="DESIGNER")
