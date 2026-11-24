from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import AwareDatetime, Field

from .base import ContractModel, HttpsUrl
from .lessons import LESSON_FORMATS

__all__ = [
    "EXPORT_FORMATS",
    "EXPORT_LINK_SCHEMA_VERSION",
    "EXPORT_LINK_SECONDS",
    "EXPORT_MEDIA_TYPES",
    "PAGE_EXPORT_FORMATS",
    "ExportLink",
]

EXPORT_LINK_SCHEMA_VERSION = 1
EXPORT_LINK_SECONDS = 300
EXPORT_MEDIA_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "html": "text/html; charset=utf-8",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
PAGE_EXPORT_FORMATS = ("pdf", "docx")
EXPORT_FORMATS = (*LESSON_FORMATS, "docx")

ExportFormat = Literal[*EXPORT_FORMATS]


class ExportLink(ContractModel):
    schema_version: Literal[1]
    format: ExportFormat
    file_name: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9_.-]+$")
    url: HttpsUrl
    expires_at: AwareDatetime
