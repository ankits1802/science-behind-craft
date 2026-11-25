from __future__ import annotations

from app.research.field_voices import FIELD_IMAGE_PROVIDERS
from app.research.image_relevance import PictureContext
from app.research.media_refs import MediaRef

from .curation_keys import MEDIA_PROVIDER
from .media_ref_store import TEXT_RELEVANCE, StoredPicture
from .picture_sites import blocked_picture

__all__ = [
    "CHOSEN_PICTURE_PROVIDERS",
    "chosen_picture",
    "searched_text_link",
    "served_picture",
]

CHOSEN_PICTURE_PROVIDERS = frozenset({MEDIA_PROVIDER, *FIELD_IMAGE_PROVIDERS})


def chosen_picture(media: MediaRef) -> bool:
    return media.provider in CHOSEN_PICTURE_PROVIDERS


def searched_text_link(picture: StoredPicture) -> bool:
    return picture.relevance == TEXT_RELEVANCE and not chosen_picture(picture.media)


def served_picture(picture: StoredPicture, context: PictureContext) -> bool:
    media = picture.media
    if blocked_picture(page_url=media.page_url, image_url=media.image_url, title=media.title):
        return False
    return not searched_text_link(picture) or context.named_in(media.title)
