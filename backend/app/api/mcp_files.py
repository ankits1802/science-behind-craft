from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, TypeAdapter, ValidationError

from app.research.base import ContractModel

from .mcp_meta import FILES_EXTENSION, RequestMeta, missing_capability

__all__ = [
    "OCTET_STREAM",
    "UPLOAD_REQUIRED",
    "FileArgument",
    "FileInput",
    "Staged",
    "file_problem",
    "file_schema",
    "given_files",
    "listed_with_files",
    "upload_required",
]

UPLOAD_REQUIRED = "upload_required"
OCTET_STREAM = "application/octet-stream"
FILE_ID_MAX = 128
NOT_FILES = "{name}: each file is {{id, name, mimeType, size}} as the files extension sends it"
TWICE = "two files in the call share the id {id}; each file has an id of its own"
INLINE = (
    "a file's bytes are not taken inside the call: send {name} out of band, as the files extension uploads it"
)
EMPTY = "{name} is empty; send the file itself"
NO_UPLOADS = "This server takes no files right now; give the words, the link or the upload slot instead."
TOO_LARGE = "{name} is {size:,} bytes; a file here is at most {most:,} bytes"
WRONG_TYPE = "{name} is {mime}; this tool takes {accepted}"


class FileDigest(ContractModel):
    algorithm: Literal["sha-256"]
    value: str = Field(min_length=1, max_length=100)


class FileInput(ContractModel):
    id: str = Field(min_length=1, max_length=FILE_ID_MAX)
    name: str | None = Field(default=None, max_length=1000)
    mime_type: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0)
    digest: FileDigest | None = None
    data: str | None = None

    @property
    def label(self) -> str:
        return self.name or self.id

    @property
    def suffix(self) -> str:
        stem, dot, ending = (self.name or "").rpartition(".")
        return f".{ending.lower()}" if dot and stem else ""


FILES = TypeAdapter(list[FileInput])


@dataclass(frozen=True)
class Staged:
    file_id: str
    url: str
    ref: str
    expires_at: datetime


Stage = Callable[[Any, Any], Awaitable[list[Staged]]]


@dataclass(frozen=True)
class FileArgument:
    name: str
    accept: tuple[str, ...]
    max_size: int
    stage: Stage
    many: bool = False
    description: str = ""

    def schema(self) -> dict[str, Any]:
        one = file_schema(self.accept, self.max_size, self.description)
        if not self.many:
            return one
        return {"type": "array", "description": self.description, "items": one}


def file_schema(accept: Sequence[str], max_size: int, description: str = "") -> dict[str, Any]:
    return {
        "type": "object",
        "description": description,
        "x-mcp-file": {"accept": list(accept), "maxSize": max_size},
        "properties": {
            "id": {"type": "string", "minLength": 1, "maxLength": FILE_ID_MAX},
            "name": {"type": "string"},
            "mimeType": {"type": "string"},
            "size": {"type": "integer", "minimum": 0},
            "digest": {
                "type": "object",
                "properties": {"algorithm": {"const": "sha-256"}, "value": {"type": "string"}},
                "required": ["algorithm", "value"],
            },
        },
        "required": ["id", "mimeType", "size"],
    }


def listed_with_files(schema: Mapping[str, Any], argument: FileArgument) -> dict[str, Any]:
    properties = {**schema.get("properties", {}), argument.name: argument.schema()}
    return {**schema, "properties": properties}


def given_files(
    arguments: Mapping[str, Any], argument: FileArgument
) -> tuple[dict[str, Any], list[FileInput]]:
    rest = {key: value for key, value in arguments.items() if key != argument.name}
    given = arguments.get(argument.name)
    if given is None:
        return rest, []
    try:
        files = FILES.validate_python(given if argument.many else [given])
    except ValidationError:
        raise ValueError(NOT_FILES.format(name=argument.name)) from None
    return rest, files


def file_problem(
    files: Sequence[FileInput], argument: FileArgument, meta: RequestMeta | None, *, enabled: bool
) -> str | None:
    seen: set[str] = set()
    for file in files:
        if file.id in seen:
            return TWICE.format(id=file.id)
        seen.add(file.id)
        if file.data is not None:
            return INLINE.format(name=file.label)
        if file.size == 0:
            return EMPTY.format(name=file.label)
    if not enabled:
        return NO_UPLOADS
    if meta is None or not meta.uploads_files():
        raise missing_capability({"extensions": {FILES_EXTENSION: {"upload": {}}}})
    return next((said for file in files if (said := _metadata_problem(file, argument))), None)


def upload_required(staged: Sequence[Staged], state: str) -> dict[str, Any]:
    return {
        "resultType": UPLOAD_REQUIRED,
        "uploads": [
            {
                "fileId": item.file_id,
                "url": item.url,
                "method": "PUT",
                "headers": {"Content-Type": OCTET_STREAM},
                "credentials": "omit",
                "expiresAt": item.expires_at.isoformat(),
            }
            for item in staged
        ],
        "requestState": state,
    }


def _metadata_problem(file: FileInput, argument: FileArgument) -> str | None:
    if file.size > argument.max_size:
        return TOO_LARGE.format(name=file.label, size=file.size, most=argument.max_size)
    typed = {kind for kind in argument.accept if not kind.startswith(".")}
    endings = {kind for kind in argument.accept if kind.startswith(".")}
    if file.mime_type in typed or file.suffix in endings or file.mime_type == OCTET_STREAM:
        return None
    return WRONG_TYPE.format(name=file.label, mime=file.mime_type, accepted=", ".join(argument.accept))
