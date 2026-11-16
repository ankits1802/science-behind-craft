from __future__ import annotations

from pathlib import PurePosixPath

from hygiene.comments import comment_violations


def check(text: str) -> list[str]:
    return [violation.describe() for violation in comment_violations([(PurePosixPath("m.py"), text)])]


def test_code_without_comments_passes() -> None:
    assert check("x = 1\n") == []


def test_a_full_line_comment_is_refused() -> None:
    assert check("x = 1\n# why we do this\ny = 2\n") == ["m.py:2: # why we do this"]


def test_a_trailing_comment_is_refused() -> None:
    assert check("x = 1  # one\n") == ["m.py:1: # one"]


def test_hash_inside_a_string_is_not_a_comment() -> None:
    assert check('colour = "#ff0000"\nquery = """\n# not a comment\n"""\n') == []


def test_functional_directives_pass() -> None:
    text = (
        "import os  # noqa: F401\n"
        "y: int = 'a'  # type: ignore[assignment]\n"
        "if False:  # pragma: no cover\n"
        "    pass\n"
        "# fmt: off\n"
    )
    assert check(text) == []


def test_a_shebang_on_the_first_line_passes_and_elsewhere_fails() -> None:
    assert check("#!/usr/bin/env python\nx = 1\n") == []
    assert check("x = 1\n#!/usr/bin/env python\n") == ["m.py:2: #!/usr/bin/env python"]


def test_a_comment_that_only_mentions_noqa_later_is_refused() -> None:
    assert check("x = 1  # see noqa docs\n") == ["m.py:1: # see noqa docs"]
