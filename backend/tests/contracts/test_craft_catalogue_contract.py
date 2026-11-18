from app.research.craft_catalogue import CraftCatalogue, catalogue_text

from .catalogue_golden import AJRAKH_PICTURE, CATALOGUE_GOLDEN, golden_catalogue
from .golden import golden_json, golden_text, reproduces

PRIVATE_FIELDS = frozenset({"email", "userId", "role", "status", "referenceCount", "mergedIntoId"})


def test_the_catalogue_golden_parses_and_matches_the_response_models() -> None:
    assert reproduces(CraftCatalogue, CATALOGUE_GOLDEN)


def test_the_catalogue_golden_is_the_assembled_catalogue_as_served() -> None:
    assert catalogue_text(CraftCatalogue.model_validate(golden_catalogue())) == golden_text(CATALOGUE_GOLDEN)


def test_the_golden_shows_every_reader_field_and_no_private_one() -> None:
    body = golden_json(CATALOGUE_GOLDEN)
    rows = {row["slug"]: row for row in body["crafts"]}
    ajrakh = rows["Kutch-Ajrakh"]
    assert ajrakh["hero"]["url"] == AJRAKH_PICTURE.image_url
    dhokra = rows["Bastar-Dhokra"]["hero"]
    assert dhokra["url"].startswith("https://upload.wikimedia.org/wikipedia/commons/thumb/")
    assert (dhokra["width"], dhokra["height"]) == (500, 375)
    assert (ajrakh["depth"]["coverage"], ajrakh["giYear"], ajrakh["palette"]) == ("FULL", 2024, "indigo")
    assert rows["Phulkari"]["localName"] == "ਫੁਲਕਾਰੀ"
    assert rows["Other-Hand-Block-Print"]["isCatchAll"] is True
    assert body["summary"]["crafts"] == sum(not row["isCatchAll"] for row in body["crafts"])
    assert body["concepts"][0]["key"] == "indigo"
    assert "Other-Hand-Block-Print" not in body["concepts"][0]["craftSlugs"]
    assert all(concept["key"] != "kutch-ajrakh" for concept in body["concepts"])
    assert not PRIVATE_FIELDS & {key for row in body["crafts"] for key in row}
