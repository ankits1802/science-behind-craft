from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field

from app.research.blocks import ExplainerSentence, StagePicture
from app.research.craft_page import PagePicture
from app.research.craft_page_context import INLINE
from app.research.craft_parts import Focal, PagePlate, PlatePart, RecordPart

from .chapter_context import ChapterContext
from .curated_index import CuratedPage, IndexPicture, IndexPlacement

__all__ = ["PicturePlan", "loose_stage_plates", "picture_plan", "placed_records"]

MASTHEAD, OPENER, PLATE, RECORD, STAGE, MATERIAL = (
    "MASTHEAD",
    "OPENER",
    "PLATE",
    "RECORD",
    "STAGE",
    "MATERIAL",
)
HERO = "HERO"
GLANCE = "glance"


@dataclass(frozen=True)
class PlacedPlate:
    chapter: str
    role: str
    plate: PagePlate
    claim_ids: tuple[uuid.UUID, ...]
    stage_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PicturePlan:
    masthead: PagePlate | None = None
    placed: tuple[PlacedPlate, ...] = field(default_factory=tuple)

    def opener(self, chapter: str) -> PagePlate | None:
        return next((p.plate for p in self.placed if p.chapter == chapter and p.role == OPENER), None)

    def plates(self, chapter: str, roles: Sequence[str] = (PLATE,)) -> list[PlacedPlate]:
        return [p for p in self.placed if p.chapter == chapter and p.role in roles]

    def stage_pictures(self, stage_id: uuid.UUID) -> list[StagePicture]:
        return [
            StagePicture(media=p.plate.media, caption=p.plate.caption, stand_in=p.plate.stand_in)
            for p in self.placed
            if p.role == STAGE and p.stage_id == stage_id
        ]


def picture_plan(ctx: ChapterContext, pictures: Sequence[PagePicture]) -> PicturePlan:
    curated = ctx.records.curated
    indexed = _indexed(curated)
    masthead: PagePlate | None = None
    placed: list[PlacedPlate] = []
    for picture in (picture for picture in pictures if picture.media.display == INLINE):
        entry = indexed.get(picture.media.id)
        placement = entry.placement if entry is not None else None
        plate = _plate(ctx, picture, entry)
        if placement is not None:
            placed.append(_placed(curated, placement, plate, picture))
        elif picture.role == HERO and masthead is None:
            masthead = plate
        elif picture.stage_id is not None:
            placed.append(PlacedPlate("made", STAGE, plate, tuple(picture.claim_ids), picture.stage_id))
        else:
            placed.append(PlacedPlate(GLANCE, PLATE, plate, tuple(picture.claim_ids)))
    chosen = next((p for p in placed if p.role == MASTHEAD), None)
    if chosen is not None:
        masthead = chosen.plate
    return PicturePlan(masthead, tuple(p for p in placed if p.role != MASTHEAD))


def _indexed(curated: CuratedPage | None) -> dict[uuid.UUID, IndexPicture]:
    return {} if curated is None else {picture.media_ref_id: picture for picture in curated.pictures}


def _plate(ctx: ChapterContext, picture: PagePicture, entry: IndexPicture | None) -> PagePlate:
    focal = entry.focal if entry is not None else None
    return PagePlate(
        media=picture.media,
        caption=picture.caption,
        stand_in=entry.stand_in if entry is not None else None,
        focal=Focal(x=focal.x, y=focal.y, width=focal.width, height=focal.height) if focal else None,
        sentences=ctx.facts(picture.claim_ids, f"plate-{str(picture.media.id)[:8]}"),
    )


def _placed(
    curated: CuratedPage | None, placement: IndexPlacement, plate: PagePlate, picture: PagePicture
) -> PlacedPlate:
    stages = {stage.key: stage.stage_id for stage in curated.stages} if curated else {}
    materials = {item.key: item.material_id for item in curated.materials} if curated else {}
    stage_id = stages.get(placement.stage_key) if placement.stage_key else picture.stage_id
    material_id = materials.get(placement.material_key) if placement.material_key else None
    claim_ids = tuple(picture.claim_ids)
    return PlacedPlate(placement.chapter, placement.role, plate, claim_ids, stage_id, material_id)


def placed_records(
    plan: PicturePlan, chapter: str, record: RecordPart | None
) -> tuple[RecordPart | None, list[PlatePart]]:
    loose: list[PlatePart] = []
    entries = list(record.entries) if record is not None else []
    for placed in plan.plates(chapter, (RECORD,)):
        wanted = {str(claim_id) for claim_id in placed.claim_ids}
        index = next(
            (n for n, entry in enumerate(entries) if entry.plate is None and _cites(entry.sentences, wanted)),
            None,
        )
        if index is None:
            loose.append(PlatePart(kind="plate", plate=placed.plate))
        else:
            entries[index] = entries[index].model_copy(update={"plate": placed.plate})
    found = record.model_copy(update={"entries": entries}) if record is not None else None
    return found, loose


def loose_stage_plates(plan: PicturePlan, shown: Collection[uuid.UUID]) -> list[PlatePart]:
    return [
        PlatePart(kind="plate", plate=placed.plate)
        for placed in plan.placed
        if placed.role == STAGE and placed.stage_id not in shown
    ]


def _cites(sentences: Sequence[ExplainerSentence], wanted: Collection[str]) -> bool:
    return any(citation.claim_id in wanted for sentence in sentences for citation in sentence.citations)
