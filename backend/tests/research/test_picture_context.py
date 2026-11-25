import uuid

from app.research.image_relevance import (
    ClaimText,
    PictureContext,
    choose_images,
    illustration,
    picture_context,
)

from .test_image_relevance import picture

GACH = ClaimText(
    uuid.UUID(int=21),
    "Stage 7, gach, stamps a khor resist of alum, gum arabic, millet flour and red clay, "
    "then a resist of lime and gum arabic.",
)
VAT = ClaimText(
    uuid.UUID(int=22),
    "Natural indigo bought in blocks is fermented in an underground vat of strong alkaline lime.",
)
AJRAKH_WORLD = PictureContext(frozenset({"kutch", "ajrakh", "print", "cloth", "block"}))


def test_a_picture_sharing_two_stems_but_naming_nothing_of_the_craft_s_world_is_refused() -> None:
    farm = picture("Clay Farm, Aura, Lime Avenue - geograph.org.uk - 6678543")
    assert illustration(farm, [GACH], leave_out="Kutch Ajrakh") is not None
    assert choose_images([farm], [GACH], leave_out="Kutch Ajrakh", context=AJRAKH_WORLD) == []


def test_a_picture_whose_title_names_the_craft_s_world_is_kept_for_the_claims_it_shares_stems_with() -> None:
    paste = picture("Lime and clay resist printing on cloth")
    (chosen,) = choose_images([paste], [GACH, VAT], leave_out="Kutch Ajrakh", context=AJRAKH_WORLD)
    assert chosen.candidate is paste
    assert chosen.illustration.claim_ids == (GACH.claim_id,)
    assert chosen.illustration.shared == 3


def test_the_world_is_named_by_the_title_never_by_a_tag_list() -> None:
    tagged = picture("Brick House iPhone Background", "art, background, block, brick, burnt, lime, masonry")
    assert illustration(tagged, [VAT], leave_out="Kutch Ajrakh") is not None
    assert choose_images([tagged], [VAT], leave_out="Kutch Ajrakh", context=AJRAKH_WORLD) == []


def test_a_title_word_holds_a_context_word_it_begins_with() -> None:
    world = PictureContext(frozenset({"print", "cotton", "kutch"}))
    assert world.named_in("Printed shawls drying")
    assert world.named_in("KUTCH'S salt desert")
    assert world.named_in("Kutchi embroidery")
    assert not world.named_in("A thatched cottage")
    assert not world.named_in("The Prince of Wales")


def test_the_context_keeps_names_and_places_less_their_ordinary_words_and_every_family_word() -> None:
    world = picture_context(
        ["Kutch Ajrakh", "Ajrakh block printing"],
        ["Dhamadka River (Suran)", "Gujarat"],
        ["cloth", "dyeing"],
        ordinary=frozenset({"block", "printing", "river", "cloth"}),
    )
    assert world.words == {"kutch", "ajrakh", "dhamadka", "suran", "gujarat", "cloth", "dyeing"}


def test_a_word_too_short_or_too_common_to_be_a_content_word_adds_nothing() -> None:
    world = picture_context(["Goa"], [], ["dye", "rug", "with"], ordinary=frozenset())
    assert world.words == frozenset()
    assert not world.named_in("Dye pots in Goa")
