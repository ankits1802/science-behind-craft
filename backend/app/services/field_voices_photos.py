from __future__ import annotations

from dataclasses import dataclass

from app.services.field_voices_credit import Credited, credit_line, person_line, workshop_line
from app.services.field_voices_items import ImageItem, Placement

__all__ = ["MEDIA_TEXT_MAX", "PhotoPlan", "photo_groups", "photo_plan"]

MEDIA_TEXT_MAX = 300
PROTOTYPE = "PROTOTYPE"
GROUP_FALLBACKS = {
    "PRODUCT": "Product",
    "TOOL": "Tool",
    "PROCESS": "Process",
    "PROCESS_STEP": "Process step",
    "PROTOTYPE": "Prototype",
    "CRAFT": "The craft",
}
FILED_GROUPS = {
    "ARTISAN": ("PERSON", "An artisan"),
    "DESIGNER": ("PERSON", "A designer"),
    "SESSION": ("SESSION", "A field session"),
    "WORKSHOP": ("WORKSHOP", "The workshop"),
    "DESIGN_WORKSHOP": ("WORKSHOP", "The design workshop"),
}


@dataclass(frozen=True)
class PhotoGroupPlan:
    kind: str
    key: str
    label: str


@dataclass(frozen=True)
class PhotoPlan:
    groups: tuple[PhotoGroupPlan, ...]
    credited: tuple[str, ...]
    credit: str
    workshop_line: str | None
    title: str
    alt: str


def photo_plan(item: ImageItem, *, portal: str) -> PhotoPlan:
    people = {person.id: person for person in item.people}
    craft = item.crafts[0].name
    credited = [Credited(people[credit.person_id], craft, None) for credit in item.credits]
    names = tuple(dict.fromkeys(person_line(each) for each in credited))
    unnamed = any(each.person.name is None for each in credited)
    day = item.taken_at.date() if item.taken_at else None
    fallback = item.workshop.starts_on if item.workshop and item.workshop.starts_on else day
    workshop = workshop_line(item.workshop, any_unnamed=unnamed, fallback_day=fallback) if fallback else None
    groups = photo_groups(item.belongs_to)
    labels = "; ".join(group.label for group in groups)
    return PhotoPlan(
        groups=groups,
        credited=names,
        credit=credit_line(names, workshop=workshop, day=day, portal=portal)[:MEDIA_TEXT_MAX],
        workshop_line=workshop,
        title=(item.caption or labels or craft)[:MEDIA_TEXT_MAX],
        alt=f"Photograph of {craft}: {item.caption or labels}"[:MEDIA_TEXT_MAX],
    )


def photo_groups(placements: tuple[Placement, ...]) -> tuple[PhotoGroupPlan, ...]:
    groups: dict[str, PhotoGroupPlan] = {}
    for placement in placements:
        group = _group(placement)
        groups.setdefault(group.key, group)
    return tuple(groups.values())


def _group(placement: Placement) -> PhotoGroupPlan:
    kind = placement.kind
    if kind == "DESIGN_STAGE":
        return _stage_group(placement)
    if kind == "PROCESS_STEP":
        label = " · ".join(part for part in (placement.process, placement.name) if part)
        return PhotoGroupPlan(kind, f"step:{placement.id}", label or GROUP_FALLBACKS[kind])
    if kind == "CRAFT":
        return PhotoGroupPlan(kind, "craft", GROUP_FALLBACKS[kind])
    if kind in FILED_GROUPS:
        group, fallback = FILED_GROUPS[kind]
        return PhotoGroupPlan(group, f"{group.lower()}:{placement.id}", placement.name or fallback)
    label = placement.name or placement.english_name or GROUP_FALLBACKS[kind]
    return PhotoGroupPlan(kind, f"{kind.lower()}:{placement.id}", label)


def _stage_group(placement: Placement) -> PhotoGroupPlan:
    stage, entity, row, field = placement.stage, placement.entity, placement.row, placement.field
    if stage is None or entity is None or row is None or field is None:
        raise ValueError("a design stage placement names its stage, entity, row and field")
    if placement.prototype_id is not None:
        label = row.label if entity.key == "prototype" and row.label else GROUP_FALLBACKS[PROTOTYPE]
        return PhotoGroupPlan(PROTOTYPE, f"prototype:{placement.prototype_id}", label)
    label = " · ".join(part for part in (stage.title, entity.label, row.label) if part)
    return PhotoGroupPlan("DESIGN_STAGE", f"stage:{stage.key}:{row.id}", f"{label} · {field.label}")
