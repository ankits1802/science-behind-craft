from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from .base import ContractModel, absent
from .craft_parts import Focal
from .evidence import personal_data_in
from .image_contributions import IMAGE_TEXT_MAX_CHARS, PictureTarget
from .knowledge_writes import STATEMENT_MAX_CHARS, STATEMENT_MIN_CHARS
from .quotes import QUOTE_OVERLAP_MIN, quote_overlap, unsupported_figures

__all__ = [
    "CHANGE_TEXT_MAX_CHARS",
    "EDIT_FIELDS_MAX",
    "NOTHING_CHANGES",
    "ComponentEdit",
    "FactEdit",
    "FieldChange",
    "PictureEdit",
    "StagedEdit",
    "edited_fields",
    "fact_text_problems",
    "field_changes",
    "field_label",
    "moved_fields",
    "shown_value",
]

EDIT_FIELDS_MAX = 8
CHANGE_TEXT_MAX_CHARS = 300
PICTURE_TEXT_MIN_CHARS = 3
SPEC_KEYS_MAX = 200
NOTHING_CHANGES = "An edit changes at least one field, and every field named here already holds that value."
NO_QUOTE = (
    "This fact has no quote to match a new text against: retract it and propose the new text with its quotes."
)
FIGURES = "{figures} in the new text appears in none of the fact's quotes."
OVERLAP = (
    "The new text says too little of what its quotes say: {share:.0%} of its words are in them, and an edit "
    "keeps at least {least:.0%}."
)
KEPT = "{fields} cannot be emptied: give the new value."


class StagedEdit(ContractModel):
    fields: dict[str, Any] = Field(min_length=1, max_length=EDIT_FIELDS_MAX)
    before: dict[str, Any] | None = Field(default=None, exclude_if=absent)


class FieldChange(ContractModel):
    field: str
    before: str | None = None
    after: str | None = None


class FactEdit(ContractModel):
    text: str = Field(min_length=STATEMENT_MIN_CHARS, max_length=STATEMENT_MAX_CHARS)

    @field_validator("text")
    @classmethod
    def _no_personal_data(cls, value: str) -> str:
        found = personal_data_in(value)
        if found:
            raise ValueError(f"a fact never carries personal data ({', '.join(found)})")
        return value


class ComponentEdit(ContractModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=600)
    spec: dict[str, Any] | None = Field(default=None, min_length=1, max_length=SPEC_KEYS_MAX)
    units: dict[str, Any] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _keeps_what_it_names(self) -> Self:
        return _kept(self, ("title", "description", "spec", "units"))


class PictureEdit(ContractModel):
    caption: str | None = Field(
        default=None, min_length=PICTURE_TEXT_MIN_CHARS, max_length=IMAGE_TEXT_MAX_CHARS
    )
    alt_text: str | None = Field(
        default=None, min_length=PICTURE_TEXT_MIN_CHARS, max_length=IMAGE_TEXT_MAX_CHARS
    )
    focal: Focal | None = None
    place: PictureTarget | None = None

    @model_validator(mode="after")
    def _keeps_what_it_names(self) -> Self:
        kept = _kept(self, ("caption", "alt_text", "place"))
        if kept.place is not None and kept.place.task_key is not None:
            raise ValueError("a picture's place names its stage, material or slot, never a task")
        return kept


def edited_fields(model: type[ContractModel], given: Mapping[str, Any]) -> dict[str, Any]:
    checked = model.model_validate(dict(given))
    dumped = checked.model_dump(mode="json", by_alias=False)
    return {name: dumped[name] for name in type(checked).model_fields if name in checked.model_fields_set}


def moved_fields(current: Mapping[str, Any], before: Mapping[str, Any]) -> list[str]:
    return [name for name, value in before.items() if _same(current.get(name)) != _same(value)]


def fact_text_problems(text: str, quotes: Sequence[str]) -> list[str]:
    if not quotes:
        return [NO_QUOTE]
    problems = []
    missing = unsupported_figures(text, quotes)
    if missing:
        problems.append(FIGURES.format(figures=", ".join(missing)))
    share = quote_overlap(text, quotes)
    if share < QUOTE_OVERLAP_MIN:
        problems.append(OVERLAP.format(share=share, least=QUOTE_OVERLAP_MIN))
    return problems


def field_changes(edit: StagedEdit) -> list[FieldChange]:
    before = edit.before or {}
    return [
        FieldChange(field=field_label(name), before=shown_value(before.get(name)), after=shown_value(value))
        for name, value in sorted(edit.fields.items())
    ]


def field_label(name: str) -> str:
    words = name.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def shown_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        shown = value
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        shown = ", ".join(value)
    else:
        shown = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return shown if len(shown) <= CHANGE_TEXT_MAX_CHARS else f"{shown[: CHANGE_TEXT_MAX_CHARS - 1]}…"


def _kept[Edited: ContractModel](edit: Edited, required: Sequence[str]) -> Edited:
    emptied = [name for name in required if name in edit.model_fields_set and getattr(edit, name) is None]
    if emptied:
        raise ValueError(KEPT.format(fields=", ".join(emptied)))
    return edit


def _same(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)
