import uuid
from functools import cache

import pytest

from app.curation.dossier import Dossier
from app.curation.files import CURATION_DIR
from app.data.craft_families import load_craft_families
from app.data.craft_master_loader import ACTIVE, load_craft_aliases, load_master
from app.data.english_words import load_english_words
from app.research.image_relevance import (
    ClaimText,
    PictureContext,
    choose_images,
    illustration,
    picture_context,
)
from app.services.section_images import stored_items

from .fakes import candidate, stored_picture

SLUG = "Kutch-Ajrakh"
TEXTILES = "Textiles-Based-Craft-Category"
GACH = ClaimText(
    uuid.UUID(int=41),
    "Stage 7, gach, stamps a khor resist of alum, gum arabic, millet flour and red clay, then a resist "
    "of lime and gum arabic, dusted against smudging.",
)
VAT = ClaimText(
    uuid.UUID(int=42),
    "The GI journal describes natural indigo bought in blocks being ground, soaked and fermented in an "
    "underground vat of strong alkaline lime, dates and carbonate of soda.",
)
RESIST = ClaimText(
    uuid.UUID(int=43),
    "Kutch Ajrakh is an elaborate resist block-printing technique built on a series of direct and "
    "resist printing and dyeing steps.",
)
BRICK_TAGS = (
    "640, 960, 960x640, adhesive, apple, art, artwork, background, beige, binding, block, brick, "
    "brickwork, burnt, cameraphone, cement, cinder, composition, cotta, cube, gap, grout, hd, hires, "
    "hoesly, illustration, image, ios, iphone, joint, lime, masonry, mineral, mortar, patrickhoesly, "
    "paving, phone"
)
FARM = candidate(
    "wikimedia_commons",
    1,
    "Clay Farm, Aura, Lime Avenue - geograph.org.uk - 6678543",
    licence="CC BY-SA 2.0",
    author="Geograph",
)
BRICK = candidate(
    "openverse",
    2,
    "Brick House iPhone Background",
    licence="CC BY 2.0",
    author="Patrick Hoesly",
    description=BRICK_TAGS,
)
CARD = candidate(
    "searxng", 3, "Ajrakh Block Printing | Crafts of Kutch - Handicrafts of Kutch", licence=None, author=None
)
KEPT = [
    ("openverse", "stretch of art, dhamadka kutch"),
    ("openverse", "feel the heat, dhamadka kutch"),
    ("searxng", "Ajrakh Block Printing | Crafts of Kutch - Handicrafts of Kutch"),
    ("wikimedia_commons", "Cotton textile structure"),
    ("curation", "Natural dye and printing materials, among them alum and lime, laid out on an ajrakh cloth"),
    ("curation", "Workers beating the vats at an indigo factory in Allahabad in 1877"),
]
REFUSED = [
    ("wikimedia_commons", "Clay Farm, Aura, Lime Avenue - geograph.org.uk - 6678543"),
    ("openverse", "Lemons and Limes, Fresh Fruit Color"),
    ("openverse", "Brick House iPhone Background"),
    ("wikimedia_commons", "Lemon and lime"),
]
STAND_IN = "Workers beating the vats at an indigo factory in Allahabad in 1877"


@cache
def kutch_ajrakh_world() -> PictureContext:
    craft = next(craft for craft in load_master() if craft.slug == SLUG)
    aliases = load_craft_aliases()["crafts"][SLUG]["aliases"]
    dossier = Dossier.model_validate_json((CURATION_DIR / f"{SLUG}.json").read_text(encoding="utf-8"))
    located = [
        part
        for place in dossier.places
        if place.state is not None
        for part in (place.name, place.district or "", place.state)
    ]
    family = load_craft_families().family(TEXTILES)
    assert family is not None
    return picture_context(
        [craft.name, *(alias["alias"] for alias in aliases if alias.get("status", ACTIVE) == ACTIVE)],
        [*craft.state_of_origin, *craft.state_of_practice, *located],
        family.picture_words,
        ordinary=load_english_words(),
    )


def served(provider: str, title: str) -> list[str]:
    found = candidate(provider, 9, title, licence="CC BY 2.0", author="A")
    return [
        item.media.title
        for item in stored_items([stored_picture(found, GACH.claim_id)], kutch_ajrakh_world())
    ]


@pytest.mark.parametrize(("provider", "title"), KEPT)
def test_the_run_s_pictures_of_the_craft_s_world_are_still_served(provider: str, title: str) -> None:
    assert served(provider, title) == [title]


@pytest.mark.parametrize(("provider", "title"), REFUSED)
def test_the_run_s_pictures_of_a_farm_fruit_and_a_wall_are_no_longer_served(
    provider: str, title: str
) -> None:
    assert served(provider, title) == []


def test_the_micrograph_names_the_family_s_world_and_the_stand_in_is_kept_by_its_curator() -> None:
    world = kutch_ajrakh_world()
    assert world.named_in("Cotton textile structure")
    assert not world.named_in(STAND_IN)
    assert served("wikimedia_commons", STAND_IN) == []
    assert served("curation", STAND_IN) == [STAND_IN]


def test_a_search_of_the_run_keeps_the_ajrakh_card_and_refuses_the_farm_and_the_wall() -> None:
    claims = [GACH, VAT, RESIST]
    assert illustration(FARM, claims, leave_out="Kutch Ajrakh") is not None
    assert illustration(BRICK, claims, leave_out="Kutch Ajrakh") is not None
    chosen = choose_images(
        [FARM, BRICK, CARD], claims, leave_out="Kutch Ajrakh", context=kutch_ajrakh_world()
    )
    assert [(image.candidate.title, image.illustration.claim_ids) for image in chosen] == [
        (CARD.title, (RESIST.claim_id,))
    ]
