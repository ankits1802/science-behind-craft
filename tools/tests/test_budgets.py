from __future__ import annotations

from pathlib import PurePosixPath

from conftest import function_source

from hygiene.budgets import FILE_LINE_BUDGET, FUNCTION_LINE_BUDGET, PARAMETER_BUDGET, measure_budgets


def measure(text: str, name: str = "pkg/mod.py"):
    return measure_budgets([(PurePosixPath(name), text)])


def test_budgets_match_the_bindings() -> None:
    assert (FILE_LINE_BUDGET, FUNCTION_LINE_BUDGET, PARAMETER_BUDGET) == (400, 40, 5)


def test_fixture_function_has_the_requested_length() -> None:
    assert len(function_source("f", 7).splitlines()) == 7


def test_a_file_of_exactly_400_lines_is_within_budget() -> None:
    assert measure("x = 1\n" * 400).oversized_files == ()


def test_a_file_of_401_lines_is_over_budget() -> None:
    (overrun,) = measure("x = 1\n" * 401).oversized_files
    assert (overrun.path, overrun.size, overrun.budget) == ("pkg/mod.py", 401, 400)


def test_function_of_40_lines_passes_and_41_fails() -> None:
    findings = measure(function_source("short", 40) + "\n\n" + function_source("long", 41))
    assert [(overrun.name, overrun.size, overrun.line) for overrun in findings.long_functions] == [
        ("long", 41, 43)
    ]


def test_nested_and_async_functions_are_measured() -> None:
    inner = function_source("inner", 41).replace("\n", "\n    ").rstrip(" ")
    text = "async def outer():\n    " + inner + "    return inner\n"
    names = sorted(overrun.name for overrun in measure(text).long_functions)
    assert names == ["inner", "outer"]


def test_five_positional_parameters_pass_and_six_fail() -> None:
    text = function_source("five", 3, parameters="a, b, c, d, e") + function_source(
        "six", 3, parameters="a, b, c, d, e, f"
    )
    assert [(overrun.name, overrun.size) for overrun in measure(text).wide_functions] == [("six", 6)]


def test_keyword_only_options_do_not_count() -> None:
    text = function_source("opts", 3, parameters="a, b, *, c, d, e, f, g")
    assert measure(text).wide_functions == ()


def test_the_receiver_of_a_method_does_not_count() -> None:
    method = function_source("go", 3, parameters="self, a, b, c, d, e").replace("\n", "\n    ").rstrip(" ")
    text = "class Thing:\n    " + method
    assert measure(text).wide_functions == ()


def test_findings_are_sorted_by_path_then_line() -> None:
    findings = measure_budgets(
        [
            (PurePosixPath("b.py"), "x = 1\n" * 401),
            (PurePosixPath("a.py"), "x = 1\n" * 402),
        ]
    )
    assert [overrun.path for overrun in findings.oversized_files] == ["a.py", "b.py"]
