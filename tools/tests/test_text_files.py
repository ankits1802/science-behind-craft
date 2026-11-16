from __future__ import annotations

from pathlib import PurePosixPath

from hygiene.text_files import encoding_violations


def check(name: str, content: bytes) -> list[str]:
    return [violation.describe() for violation in encoding_violations([(PurePosixPath(name), content)])]


def test_plain_utf8_with_lf_passes() -> None:
    assert check("docs/PLAN.md", "Kalamkari कला\n".encode()) == []


def test_byte_order_mark_is_refused() -> None:
    assert check("a.py", b"\xef\xbb\xbfx = 1\n") == ["a.py: starts with a UTF-8 byte-order mark"]


def test_crlf_line_endings_are_refused() -> None:
    assert check("a.ts", b"let a = 1;\r\nlet b = 2;\r\n") == [
        "a.ts: has a carriage return; line endings must be LF"
    ]


def test_invalid_utf8_names_the_first_bad_byte() -> None:
    assert check("a.txt", b"ok \xff\n") == ["a.txt: is not valid UTF-8 at byte 3"]


def test_latin1_text_is_refused() -> None:
    assert check("notes.md", "café\n".encode("latin-1")) == ["notes.md: is not valid UTF-8 at byte 3"]


def test_registered_binary_suffixes_are_skipped() -> None:
    assert check("frontend/fonts/inter.woff2", b"\x00\xff\r\n") == []
    assert check("public/IMAGE.PNG", b"\x89PNG\r\n\x1a\n") == []


def test_unregistered_binary_content_is_refused() -> None:
    assert check("data/blob.bin", b"ab\x00cd") == [
        "data/blob.bin: has a NUL byte; add its suffix to BINARY_SUFFIXES if it is binary"
    ]


def test_every_problem_of_one_file_is_reported() -> None:
    assert check("b.json", b"\xef\xbb\xbf{}\r\n") == [
        "b.json: has a carriage return; line endings must be LF",
        "b.json: starts with a UTF-8 byte-order mark",
    ]
