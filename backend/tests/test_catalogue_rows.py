import uuid
from datetime import UTC, datetime
from typing import Any

from app.research.craft_catalogue import CatalogueCraft, CatalogueCraftRecord
from app.research.media_refs import MediaRef
from app.services.catalogue_rows import (
    EMPTY_DEPTH,
    ConceptLink,
    catalogue_concepts,
    catalogue_hero,
    catalogue_summary,
    curated_hero,
    local_name_of,
    material_link,
)
from app.services.curated_index import IndexPicture

STATES = frozenset({"Gujarat", "Rajasthan", "Punjab"})
COMMONS_FILE = "https://upload.wikimedia.org/wikipedia/commons/e/e4/Ajrak_Craft_artisan.jpeg"
COMMONS_THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Ajrak_Craft_artisan.jpeg/500px-Ajrak_Craft_artisan.jpeg"


def craft(slug: str, **fields: Any) -> CatalogueCraft:
    values: dict[str, Any] = {
        "id": slug,
        "slug": slug,
        "name": slug,
        "display_name": slug,
        "local_name": None,
        "category_id": "textiles",
        "sub_category_id": "block-printing",
        "family_label": "Textiles",
        "kind_label": "Hand block printing",
        "palette": "indigo",
        "source_serial": None,
        "state_of_origin": [],
        "state_of_practice": [],
        "gi_status": "NON_GI",
        "gi_year": None,
        "is_catch_all": False,
        "craft_code": None,
        "aliases": [],
        "hero": None,
        "depth": EMPTY_DEPTH,
    }
    values.update(fields)
    return CatalogueCraft(**values)


def media(**fields: Any) -> MediaRef:
    values: dict[str, Any] = {
        "id": uuid.UUID(int=1),
        "display": "INLINE",
        "provider": "curation",
        "page_url": "https://commons.wikimedia.org/wiki/File:Ajrak_Craft_artisan.jpeg",
        "image_url": COMMONS_FILE,
        "width": None,
        "height": None,
        "title": "An ajrakh artisan",
        "alt": "An ajrakh artisan",
        "author": "Visdaviva",
        "site": "commons.wikimedia.org",
        "credit": None,
        "licence": "CC BY-SA 3.0",
        "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "source_id": None,
        "retrieved_at": datetime(2026, 11, 17, tzinfo=UTC),
    }
    values.update(fields)
    return MediaRef(**values)


def test_the_summary_counts_readers_not_catch_all_or_retired_rows() -> None:
    rows = [
        craft("ajrakh", gi_status="GI", state_of_practice=["Gujarat"]),
        craft("lace", state_of_practice=["All India"]),
        craft("other-prints", gi_status="GI", is_catch_all=True, state_of_practice=["Rajasthan"]),
        craft("located", state_of_practice=["All India"], sub_category_id="embroidery"),
        CatalogueCraftRecord(
            **craft("retired", gi_status="GI", state_of_practice=["Punjab"]).model_dump(),
            status="LEGACY",
            merged_into_id=None,
            reference_count=0,
        ),
    ]
    summary = catalogue_summary(rows, frozenset({"located"}), STATES)
    assert summary.model_dump(by_alias=False) == {
        "crafts": 3,
        "gi_registered": 1,
        "states": 1,
        "placed": 2,
        "families": 1,
        "kinds": 2,
    }


def test_concepts_lead_with_the_most_shared_and_never_name_a_craft_or_a_catch_all() -> None:
    readers = {"a": "Kutch-Ajrakh", "b": "Bagru-Hand-Block-Print"}
    links = [
        ConceptLink("indigo", "Indigo", ("neel",), "a"),
        ConceptLink("indigo", "Indigo", ("nil",), "b"),
        ConceptLink("alum", "Alum", (), "b"),
        ConceptLink("alum", "Alum", (), "catch-all"),
        ConceptLink("kutch-ajrakh", "Kutch Ajrakh", (), "a"),
        ConceptLink("beeswax", "Beeswax", (), "unknown"),
    ]
    concepts = catalogue_concepts(links, readers, frozenset({"kutch-ajrakh"}))
    assert [concept.model_dump(by_alias=False) for concept in concepts] == [
        {
            "key": "indigo",
            "label": "Indigo",
            "names": ["neel", "nil"],
            "craft_slugs": sorted(readers.values()),
        },
        {"key": "alum", "label": "Alum", "names": [], "craft_slugs": ["Bagru-Hand-Block-Print"]},
    ]


def test_a_material_is_keyed_on_its_head_word_and_keeps_its_gloss_as_a_name() -> None:
    assert material_link("Myrobalan (harda)", "a") == ConceptLink("myrobalan", "Myrobalan", ("harda",), "a")
    assert material_link("Gum arabic (babul gum)", "a") == ConceptLink(
        "gum-arabic", "Gum arabic", ("babul gum",), "a"
    )
    assert material_link("Molasses (jaggery, gur)", "a") == ConceptLink(
        "molasses", "Molasses", ("jaggery", "gur"), "a"
    )
    assert material_link("Indigo", "a") == ConceptLink("indigo", "Indigo", (), "a")
    assert material_link("ਫੁਲਕਾਰੀ", "a") is None


def test_the_local_name_comes_from_a_sourced_alias_in_the_state_language() -> None:
    languages = {"Punjab": ("pa",), "Haryana": ("hi",), "Gujarat": ("gu",)}
    aliases = [
        {"alias": "phulkari", "script": "Latn", "lang": "pa", "source": "WIKIDATA", "status": "ACTIVE"},
        {"alias": "ਫੁਲਕਾਰੀ ਕਢਾਈ", "script": "Guru", "lang": "pa", "source": "WIKIDATA", "status": "ACTIVE"},
        {"alias": "ਫੁਲਕਾਰੀ", "script": "Guru", "lang": "pa", "source": "WIKIDATA", "status": "ACTIVE"},
        {
            "alias": "ਫੁਲਕਾਰੀ ਸੂਈ",
            "script": "Guru",
            "lang": "pa",
            "source": "TRANSLITERATION",
            "status": "ACTIVE",
        },
        {"alias": "फुलकारी", "script": "Deva", "lang": "hi", "source": "WIKIDATA", "status": "ACTIVE"},
        {"alias": "ફુલકારી", "script": "Gujr", "lang": "gu", "source": "WIKIDATA", "status": "REJECTED"},
    ]
    assert local_name_of(["Punjab", "Haryana"], aliases, languages) == "ਫੁਲਕਾਰੀ"
    assert local_name_of(["Haryana", "Punjab"], aliases, languages) == "फुलकारी"
    assert local_name_of(["Gujarat"], aliases, languages) is None
    assert local_name_of(["All India"], aliases, languages) is None
    curated = [*aliases, {"alias": "ਫੁਲਕਾਰੀ ਕਲਾ", "script": "Guru", "lang": "pa", "source": "CURATED"}]
    assert local_name_of(["Punjab"], curated, languages) == "ਫੁਲਕਾਰੀ ਕਲਾ"


def test_a_hero_is_a_licensed_inline_picture_sized_for_a_card() -> None:
    hero = catalogue_hero(media())
    assert hero is not None
    assert (hero.url, hero.width, hero.height) == (COMMONS_FILE, None, None)
    assert (hero.author, hero.licence, hero.site) == ("Visdaviva", "CC BY-SA 3.0", "commons.wikimedia.org")
    sized = catalogue_hero(media(width=3000, height=2000))
    assert sized is not None and (sized.url, sized.width, sized.height) == (COMMONS_THUMB, 500, 333)
    small = catalogue_hero(media(width=400, height=300))
    assert small is not None and (small.url, small.width, small.height) == (COMMONS_FILE, 400, 300)
    exact = catalogue_hero(media(width=500, height=250))
    assert exact is not None and (exact.url, exact.width, exact.height) == (COMMONS_FILE, 500, 250)
    flickr = "https://live.staticflickr.com/4117/4929397431_d5cebd3520_b.jpg"
    elsewhere = catalogue_hero(media(image_url=flickr))
    assert elsewhere is not None and elsewhere.url == flickr
    assert catalogue_hero(media(display="LINK_CARD", licence=None, licence_url=None)) is None


def test_the_hero_is_the_first_unstaged_inline_picture_as_on_the_craft_page() -> None:
    staged = media(id=uuid.UUID(int=1))
    loose = media(
        id=uuid.UUID(int=2),
        image_url="https://upload.wikimedia.org/wikipedia/commons/a/a0/Loose.jpg",
        width=1200,
        height=900,
    )
    linked = media(id=uuid.UUID(int=3), display="LINK_CARD", licence=None, licence_url=None)
    pictures = [
        IndexPicture(key="I03", media_ref_id=linked.id, caption="Linked", stage_key=None, claim_ids=[]),
        IndexPicture(key="I01", media_ref_id=staged.id, caption="Staged", stage_key="P01", claim_ids=[]),
        IndexPicture(key="I02", media_ref_id=loose.id, caption="Loose", stage_key=None, claim_ids=[]),
    ]
    found = {item.id: item for item in (staged, loose, linked)}
    hero = curated_hero(pictures, found)
    assert hero is not None
    assert hero.url == "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Loose.jpg/500px-Loose.jpg"
    assert curated_hero(pictures[:1], found) is None
    assert curated_hero([], found) is None
