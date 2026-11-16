import httpx
import pytest

from app.api.multipart_form import form_file
from app.core.errors import InvalidInput

AUDIO = b"\x1aE\xdf\xa3\r\n\r\n--not-the-boundary\r\n\x00\xff" * 50


def encoded(files: dict[str, tuple[str, bytes, str]]) -> tuple[str, bytes]:
    request = httpx.Request("POST", "https://api.test/upload", files=files)
    return request.headers["content-type"], request.read()


def test_the_recording_comes_back_byte_for_byte() -> None:
    content_type, body = encoded({"audio": ("KalaVigyan_Voice-Session.webm", AUDIO, "audio/webm")})
    upload = form_file(content_type, body, "audio")
    assert upload.content == AUDIO and upload.content_type == "audio/webm"


def test_a_codecs_parameter_is_read_as_the_bare_type() -> None:
    content_type, body = encoded({"audio": ("a.webm", b"abc", "audio/webm;codecs=opus")})
    assert form_file(content_type, body, "audio").content_type == "audio/webm"


def test_a_missing_or_doubled_field_is_refused() -> None:
    content_type, body = encoded({"file": ("a.webm", b"abc", "audio/webm")})
    with pytest.raises(InvalidInput, match="0 'audio' fields"):
        form_file(content_type, body, "audio")
    request = httpx.Request(
        "POST",
        "https://api.test/upload",
        files=[("audio", ("a", b"1", "audio/webm")), ("audio", ("b", b"2", "audio/webm"))],
    )
    with pytest.raises(InvalidInput, match="2 'audio' fields"):
        form_file(request.headers["content-type"], request.read(), "audio")


def test_a_body_that_is_not_form_data_is_refused() -> None:
    with pytest.raises(InvalidInput, match="not multipart"):
        form_file("audio/webm", AUDIO, "audio")
    content_type, body = encoded({"audio": ("a.webm", b"abc", "audio/webm")})
    with pytest.raises(InvalidInput, match="not closed"):
        form_file(content_type, body[:-10], "audio")
