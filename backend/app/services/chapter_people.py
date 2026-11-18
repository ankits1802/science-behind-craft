from __future__ import annotations

from collections.abc import Sequence

from app.research.blocks_people import ArtisanVoiceBlock
from app.research.craft_page import PageCommunity
from app.research.craft_parts import (
    ChapterCommunity,
    CommunitiesPart,
    FamilyLink,
    FieldPhotosPart,
    PlatePart,
    RelativesPart,
)
from app.research.field_voices import FIELD_VOICES_SHOWN
from app.research.voices import VoiceQuote

from .chapter_context import ChapterContext
from .chapter_draft import ChapterDraft, Drafted
from .chapter_plates import PicturePlan

__all__ = ["kin_chapter", "people_chapter"]

PEOPLE, KIN = "people", "kin"
VOICE_FIELDS = frozenset(VoiceQuote.model_fields)


def people_chapter(
    ctx: ChapterContext, plan: PicturePlan, communities: Sequence[PageCommunity]
) -> ChapterDraft:
    items: list[Drafted] = []
    groups = _communities(ctx, communities)
    if groups is not None:
        items.append(Drafted.of_part(groups))
    voices = ctx.records.field_voices
    quotes = [VoiceQuote.model_validate(voice.model_dump(include=VOICE_FIELDS)) for voice in voices.voices]
    if quotes:
        block = ArtisanVoiceBlock(
            id="people.voices",
            kind="artisan_voice",
            version=2,
            reuse=None,
            quotes=quotes[:FIELD_VOICES_SHOWN],
        )
        items.append(Drafted.of_block(block))
    if voices.photos:
        part = FieldPhotosPart(
            kind="field_photos",
            photos=list(voices.photos),
            total=max(voices.totals.images, len(voices.photos)),
        )
        items.append(Drafted.of_part(part))
    items += [Drafted.of_part(PlatePart(kind="plate", plate=p.plate)) for p in plan.plates(PEOPLE)]
    return ChapterDraft(PEOPLE, plan.opener(PEOPLE), items)


def kin_chapter(ctx: ChapterContext, plan: PicturePlan) -> ChapterDraft:
    items: list[Drafted] = []
    family = ctx.rows.family
    link = (
        FamilyLink(label=family.label, path=family.path)
        if family is not None and family.index is not None
        else None
    )
    relatives = list(ctx.records.relatives)
    if relatives or link is not None:
        items.append(Drafted.of_part(RelativesPart(kind="relatives", crafts=relatives, family=link)))
    return ChapterDraft(KIN, plan.opener(KIN), items)


def _communities(ctx: ChapterContext, communities: Sequence[PageCommunity]) -> CommunitiesPart | None:
    shown = []
    for group in communities:
        sentences = ctx.facts(group.claim_ids, f"people.{group.key.lower()}")
        if sentences:
            shown.append(
                ChapterCommunity(
                    key=group.key,
                    kind=group.kind,
                    name=group.name,
                    local_names=group.local_names,
                    honours=group.honours,
                    place=group.place,
                    place_key=group.place_key,
                    sentences=sentences,
                )
            )
    return CommunitiesPart(kind="communities", communities=shown) if shown else None
