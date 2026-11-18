from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.data.craft_master_loader import seed_plan
from app.research.craft_catalogue import CatalogueDepth
from app.research.media_refs import MediaRef
from app.services.catalogue_rows import CatalogueExtras, ConceptLink, catalogue_hero, material_link
from app.services.craft_catalogue import assemble_catalogue

CATALOGUE_GOLDEN = "craft.catalogue.golden.json"
GOLDEN_CATEGORIES = ("Textiles-Based-Craft-Category", "Metal-Craft-Category")
GOLDEN_CRAFTS = (
    "Kutch-Ajrakh",
    "Bagru-Hand-Block-Print",
    "Sanganeri-Hand-Block-Printing",
    "Other-Hand-Block-Print",
    "Phulkari",
    "Bastar-Dhokra",
    "Metal-Embosing",
    "Brass-And-Bell-Metal-Craft",
)
AJRAKH_PICTURE = MediaRef(
    id=uuid.UUID("6f1c2a52-7b8e-5d1a-9c4e-2b3a4d5e6f70"),
    display="INLINE",
    provider="curation",
    page_url="https://commons.wikimedia.org/wiki/File:Ajrak_Craft_artisan.jpeg",
    image_url="https://upload.wikimedia.org/wikipedia/commons/e/e4/Ajrak_Craft_artisan.jpeg",
    width=None,
    height=None,
    title="An ajrakh artisan from Kutch holding up a printed ajrakh with its central field and borders",
    alt="An ajrakh artisan from Kutch holding up a printed ajrakh with its central field and borders",
    author="Visdaviva",
    site="commons.wikimedia.org",
    credit=None,
    licence="CC BY-SA 3.0",
    licence_url="https://creativecommons.org/licenses/by-sa/3.0/",
    source_id=None,
    retrieved_at=datetime(2026, 11, 17, 18, 17, tzinfo=UTC),
)
DHOKRA_PICTURE = MediaRef(
    id=uuid.UUID("0d9e8f7a-6b5c-5d4e-8f3a-2b1c0d9e8f7a"),
    display="INLINE",
    provider="curation",
    page_url="https://commons.wikimedia.org/wiki/File:AT_WORKSHOP.jpg",
    image_url="https://upload.wikimedia.org/wikipedia/commons/5/54/AT_WORKSHOP.jpg",
    width=3264,
    height=2448,
    title="Working on a figure at a workshop in Kondagaon, Bastar (2006)",
    alt="Working on a figure at a workshop in Kondagaon, Bastar (2006)",
    author="Sushilsakhuja",
    site="commons.wikimedia.org",
    credit=None,
    licence="CC BY-SA 3.0",
    licence_url="https://creativecommons.org/licenses/by-sa/3.0/",
    source_id=None,
    retrieved_at=datetime(2026, 11, 17, 23, 46, tzinfo=UTC),
)


def golden_rows() -> dict[str, list[dict[str, Any]]]:
    plan = seed_plan()
    categories = [row for row in plan["categories"] if row["slug"] in GOLDEN_CATEGORIES]
    category_ids = {row["id"] for row in categories}
    crafts = [row for row in plan["crafts"] if row["slug"] in GOLDEN_CRAFTS]
    craft_ids = {row["id"] for row in crafts}
    codes = {row["craftCode"] for row in crafts if row["craftCode"]}
    return {
        "categories": categories,
        "subCategories": [row for row in plan["subCategories"] if row["categoryId"] in category_ids],
        "crafts": crafts,
        "spellings": [row for row in plan["spellings"] if row["craftCode"] in codes],
        "aliases": [row for row in plan["aliases"] if row["craftId"] in craft_ids],
    }


def golden_extras(ids: dict[str, str]) -> CatalogueExtras:
    ajrakh, bagru, sanganeri, dhokra = (
        ids["Kutch-Ajrakh"],
        ids["Bagru-Hand-Block-Print"],
        ids["Sanganeri-Hand-Block-Printing"],
        ids["Bastar-Dhokra"],
    )
    return CatalogueExtras(
        depth={
            ajrakh: CatalogueDepth(coverage="FULL", claims=132, stages=14, pictures=4, places=12),
            dhokra: CatalogueDepth(coverage="FULL", claims=140, stages=13, pictures=3, places=7),
            sanganeri: CatalogueDepth(coverage=None, claims=48, stages=9, pictures=0, places=0),
        },
        heroes={ajrakh: _hero(AJRAKH_PICTURE), dhokra: _hero(DHOKRA_PICTURE)},
        gi_years={ajrakh: 2024, dhokra: 2008, bagru: 2011},
        located=frozenset({ajrakh, dhokra}),
        concepts=_links(ids),
    )


def golden_catalogue() -> dict[str, Any]:
    rows = golden_rows()
    ids = {row["slug"]: row["id"] for row in rows["crafts"]}
    return assemble_catalogue(
        rows["categories"],
        rows["subCategories"],
        rows["crafts"],
        rows["spellings"],
        rows["aliases"],
        extras=golden_extras(ids),
    )


def _hero(media: MediaRef) -> Any:
    hero = catalogue_hero(media)
    assert hero is not None
    return hero


def _links(ids: dict[str, str]) -> tuple[ConceptLink, ...]:
    terms = [
        ConceptLink("indigo", "Indigo", ("neel",), ids["Kutch-Ajrakh"]),
        ConceptLink("indigo", "Indigo", (), ids["Bagru-Hand-Block-Print"]),
        ConceptLink("indigo", "Indigo", (), ids["Sanganeri-Hand-Block-Printing"]),
        ConceptLink("indigo", "Indigo", (), ids["Other-Hand-Block-Print"]),
        ConceptLink("potassium-alum", "Potassium alum", ("fitkari",), ids["Kutch-Ajrakh"]),
        ConceptLink("potassium-alum", "Potassium alum", (), ids["Bagru-Hand-Block-Print"]),
        ConceptLink(
            "printing-the-mordants", "Printing the mordants", (), ids["Sanganeri-Hand-Block-Printing"]
        ),
        ConceptLink("lost-wax-casting", "Lost-wax casting", ("cire perdue",), ids["Bastar-Dhokra"]),
        ConceptLink("kutch-ajrakh", "Kutch Ajrakh", ("ajrak",), ids["Kutch-Ajrakh"]),
    ]
    materials = [
        material_link("Myrobalan (harda)", ids["Kutch-Ajrakh"]),
        material_link("Harda (myrobalan)", ids["Bagru-Hand-Block-Print"]),
        material_link("Beeswax", ids["Bastar-Dhokra"]),
        material_link("Indigo", ids["Kutch-Ajrakh"]),
    ]
    return (*terms, *(link for link in materials if link is not None))
