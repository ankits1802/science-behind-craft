from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .base import ContractModel
from .structure_proposals import (
    BOTANICAL_NAME,
    CONFLICT,
    GI_RECORD,
    GLOSSARY_TERM,
    NATIVE_NAME,
    OPEN_QUESTION,
    REACTION,
    STAGE_AFTER,
    STAGE_WHY,
)

__all__ = [
    "EDITS",
    "REMOVABLE_ENTRIES",
    "UNEDITED",
    "BotanicalNameEdit",
    "ConflictEdit",
    "GiRecordEdit",
    "GlossaryTermEdit",
    "NativeNameEdit",
    "OpenQuestionEdit",
    "StageAfterEdit",
]

REMOVABLE_ENTRIES = (
    STAGE_AFTER,
    STAGE_WHY,
    NATIVE_NAME,
    REACTION,
    BOTANICAL_NAME,
    GLOSSARY_TERM,
    CONFLICT,
    OPEN_QUESTION,
    GI_RECORD,
)
UNEDITED: Mapping[str, str] = MappingProxyType(
    {
        STAGE_WHY: "A stage's why is the fact it rests on: edit that fact instead.",
        REACTION: (
            "A reaction's equation is balanced and checked when it is proposed: remove it and propose the "
            "corrected reaction with propose_structure."
        ),
    }
)


class StageAfterEdit(ContractModel):
    text: str | None = None
    colours: list[str] | None = None


class NativeNameEdit(ContractModel):
    text: str | None = None
    language: str | None = None
    script: str | None = None


class BotanicalNameEdit(ContractModel):
    botanical_name: str | None = None


class GlossaryTermEdit(ContractModel):
    meaning: str | None = None
    language: str | None = None
    script: str | None = None


class ConflictEdit(ContractModel):
    about: str | None = None


class OpenQuestionEdit(ContractModel):
    question: str | None = None
    settled_by: str | None = None


class GiRecordEdit(ContractModel):
    application_number: str | None = None
    certificate_number: str | None = None
    filed_on: str | None = None
    registered_on: str | None = None
    journal_issue: str | None = None
    proprietors: list[str] | None = None
    authorised_user_count: int | None = None


EDITS: Mapping[str, type[ContractModel]] = MappingProxyType(
    {
        STAGE_AFTER: StageAfterEdit,
        NATIVE_NAME: NativeNameEdit,
        BOTANICAL_NAME: BotanicalNameEdit,
        GLOSSARY_TERM: GlossaryTermEdit,
        CONFLICT: ConflictEdit,
        OPEN_QUESTION: OpenQuestionEdit,
        GI_RECORD: GiRecordEdit,
    }
)
