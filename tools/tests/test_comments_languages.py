from __future__ import annotations

from pathlib import PurePosixPath

from hygiene.comments import comment_language, comment_violations


def check(name: str, text: str) -> list[str]:
    return [violation.describe() for violation in comment_violations([(PurePosixPath(name), text)])]


def test_python_docstrings_are_refused_on_modules_classes_and_functions() -> None:
    text = '"""Module."""\n\n\nclass A:\n    """Class."""\n\n\ndef f():\n    """Function."""\n    return 1\n'
    assert check("m.py", text) == ["m.py:1: docstring", "m.py:5: docstring", "m.py:9: docstring"]


def test_a_python_string_that_is_not_first_is_not_a_docstring() -> None:
    assert check("m.py", 'def f():\n    x = 1\n    "not a docstring"\n    return x\n') == []


def test_hash_languages_refuse_full_line_comments() -> None:
    assert check("w.yml", "on: push\n# why\njobs: {}\n") == ["w.yml:2: # why"]
    assert check("run.sh", "#!/usr/bin/env bash\n  # step one\necho hi\n") == ["run.sh:2: # step one"]
    assert check(".gitignore", "# build output\ndist/\n") == [".gitignore:1: # build output"]


def test_hash_languages_keep_values_and_directives() -> None:
    assert check("w.yml", 'colour: "#ff0000"\nurl: https://x.org/a#b\n') == []
    assert check("run.sh", "#!/bin/sh\n# shellcheck disable=SC2086\necho $A\n") == []


def test_script_languages_refuse_line_trailing_and_block_comments() -> None:
    text = "// header\nconst a = 1; // why\n/* block */\nreturn <div>{/* jsx */}</div>;\n"
    assert check("a.tsx", text) == [
        "a.tsx:1: // header",
        "a.tsx:2: const a = 1; // why",
        "a.tsx:3: /* block */",
        "a.tsx:4: return <div>{/* jsx */}</div>;",
    ]


def test_script_languages_keep_strings_urls_and_directives() -> None:
    text = (
        'const u = "https://example.org/x";\n'
        "const g = 'src/**/*.ts';\n"
        "const t = `a // b`;\n"
        "// eslint-disable-next-line no-console\n"
        '/// <reference types="next" />\n'
    )
    assert check("a.ts", text) == []


def test_css_refuses_block_comments_and_keeps_protocol_relative_urls() -> None:
    assert check("s.css", "a { background: url(//cdn.example/x.png); }\n/* note */\n") == [
        "s.css:2: /* note */"
    ]


def test_terraform_refuses_hash_and_slash_comments() -> None:
    assert check("m.tf", '# one\nname = "a"\n// two\n') == ["m.tf:1: # one", "m.tf:3: // two"]


def test_markup_refuses_html_comments() -> None:
    assert check("p.html", "<p>a</p>\n<!-- hidden -->\n") == ["p.html:2: <!-- hidden -->"]


def test_vendored_and_unknown_files_are_not_checked() -> None:
    assert comment_language(PurePosixPath("backend/app/data/exports/reveal/reveal.js")) is None
    assert comment_language(PurePosixPath(".claude/skills/security-audit/x.cjs")) is None
    assert comment_language(PurePosixPath("docs/README.md")) is None
    assert check("docs/README.md", "# Heading\n") == []
