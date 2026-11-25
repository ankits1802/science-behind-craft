import uuid
from datetime import UTC, datetime

from app.research.image_relevance import (
    SECTION_IMAGES_MAX,
    SECTION_LINK_CARDS_MAX,
    ClaimText,
    PictureContext,
    choose_images,
    illustration,
    topic_words,
)
from app.research.images import ImageCandidate

RETRIEVED = datetime(2026, 11, 17, 10, 20, tzinfo=UTC)
PRINTED_OVER = ClaimText(uuid.UUID(int=1), "Indigo is printed over the gum resist.")
WASHED = ClaimText(uuid.UUID(int=2), "The cloth is washed in the river.")
STICKY = ClaimText(uuid.UUID(int=3), "Printing with sticky gums takes skill.")
PRINTING_WORLD = PictureContext(frozenset({"print"}))


def picture(
    title: str,
    description: str | None = None,
    *,
    n: int = 1,
    licence: str | None = "CC BY-SA 4.0",
    author: str | None = "SMarndi",
) -> ImageCandidate:
    return ImageCandidate(
        provider="wikimedia_commons",
        page_url=f"https://commons.wikimedia.org/wiki/File:{n}.jpg",
        image_url=f"https://upload.wikimedia.org/{n}.jpg",
        original_url=f"https://upload.wikimedia.org/original/{n}.jpg",
        title=title,
        description=description,
        author=author,
        site="Wikimedia Commons",
        licence=licence,
        retrieved_at=RETRIEVED,
    )


GUMS = picture("Ajrak Printing Materials 1", "Sticky gums used during indigo printing.")


def test_an_image_illustrates_the_claims_it_shares_two_content_stems_with_beyond_the_craft_name() -> None:
    found = illustration(GUMS, [PRINTED_OVER, WASHED, STICKY], leave_out="Kutch Ajrakh")
    assert found is not None
    assert found.claim_ids == (STICKY.claim_id, PRINTED_OVER.claim_id)
    assert found.shared == 3


def test_words_of_the_craft_name_do_not_make_an_image_relevant() -> None:
    craft_only = picture("Ajrak shawl from Kutch", "Kutch ajrak shawl.")
    claim = ClaimText(uuid.UUID(int=4), "Kutch ajrak printers soak the cloth.")
    assert illustration(craft_only, [claim], leave_out="Kutch Ajrak") is None
    assert illustration(craft_only, [claim], leave_out="") is not None


def test_inline_pictures_come_first_and_link_cards_are_capped() -> None:
    cards = [picture(f"Sticky gums printing {n}", n=n, licence=None, author=None) for n in range(1, 5)]
    inline = picture("Indigo printing with sticky gums", n=9)
    chosen = choose_images([*cards, inline], [STICKY], leave_out="Kutch Ajrakh", context=PRINTING_WORLD)
    assert chosen[0].candidate is inline
    assert len(chosen) == 1 + SECTION_LINK_CARDS_MAX
    assert len(chosen) <= SECTION_IMAGES_MAX


def test_the_same_original_image_from_two_services_is_chosen_once() -> None:
    first = picture("Sticky gums printing", n=1)
    again = first.model_copy(update={"provider": "openverse", "page_url": "https://www.example.org/other"})
    chosen = choose_images([first, again], [STICKY], leave_out="", context=PRINTING_WORLD)
    assert [image.candidate.provider for image in chosen] == ["wikimedia_commons"]


def test_topic_words_are_the_most_shared_claim_words_outside_the_craft_name() -> None:
    claims = [
        ClaimText(uuid.UUID(int=5), "Resist paste is printed on Ajrakh cloth."),
        ClaimText(uuid.UUID(int=6), "The resist keeps Ajrakh outlines white."),
        ClaimText(uuid.UUID(int=7), "Paste dries in the sun."),
    ]
    assert topic_words(claims, leave_out="Kutch Ajrakh") == ["resist", "paste"]
