from __future__ import annotations

from dataclasses import dataclass
from email.message import Message

from fastapi import Request

from app.core.errors import InvalidInput

__all__ = ["BodyTooLarge", "FormFile", "form_file", "limited_body"]

HEADER_END = b"\r\n\r\n"
LINE_END = b"\r\n"


class BodyTooLarge(InvalidInput):
    pass


@dataclass(frozen=True)
class FormFile:
    content_type: str
    content: bytes


async def limited_body(request: Request, limit: int) -> bytes:
    collected = bytearray()
    async for chunk in request.stream():
        collected += chunk
        if len(collected) > limit:
            raise BodyTooLarge(f"The body is over {limit} bytes")
    return bytes(collected)


def form_file(content_type: str | None, body: bytes, field: str) -> FormFile:
    header = _header(content_type or "")
    boundary = header.get_param("boundary")
    if header.get_content_type() != "multipart/form-data" or not isinstance(boundary, str) or not boundary:
        raise InvalidInput("The upload is not multipart form data")
    delimiter = b"--" + boundary.encode("latin-1")
    segments = body.split(delimiter)
    if len(segments) < 3 or not segments[-1].startswith(b"--"):
        raise InvalidInput("The upload's form data is not closed")
    found = [part for part in map(_part, segments[1:-1]) if part[0] == field]
    if len(found) != 1:
        raise InvalidInput(f"The upload carries {len(found)} {field!r} fields, not one")
    _, part_type, content = found[0]
    return FormFile(content_type=part_type, content=content)


def _part(segment: bytes) -> tuple[str | None, str, bytes]:
    if not segment.startswith(LINE_END) or not segment.endswith(LINE_END) or HEADER_END not in segment:
        raise InvalidInput("A form data part is malformed")
    head, content = segment[len(LINE_END) : -len(LINE_END)].split(HEADER_END, 1)
    headers = Message()
    for line in head.decode("latin-1").split("\r\n"):
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip()] = value.strip()
    disposition = Message()
    disposition["content-type"] = (
        "form-data; " + str(headers.get("content-disposition", "")).partition(";")[2]
    )
    name = disposition.get_param("name")
    return (name if isinstance(name, str) else None), headers.get_content_type(), content


def _header(value: str) -> Message:
    header = Message()
    header["content-type"] = value
    return header
