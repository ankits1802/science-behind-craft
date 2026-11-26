from __future__ import annotations

import io
import warnings
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, closing
from datetime import date, datetime, time
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.workbook.workbook import Workbook

__all__ = [
    "SHEET_NAME_MAX_CHARS",
    "WORKBOOK_TYPES",
    "XLSX_TYPE",
    "WorkbookRefused",
    "is_workbook",
    "workbook_lines",
]

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
WORKBOOK_TYPES = (XLSX_TYPE,)
SHEET_NAME_MAX_CHARS = 31
ZIP_SIGNATURE = b"PK\x03\x04"
UNPACKED_BYTES_MAX = 64 * 1024 * 1024
SHEET_ROWS_READ_MAX = 100_000
SIGNIFICANT_DIGITS = 15
CONTENT_TYPES = "[Content_Types].xml"
WORKBOOK_PART = "xl/workbook.xml"
OPEN_DOCUMENT_MARK = "mimetype"
MACRO_PARTS = ("vbaproject.bin", "xl/macrosheets/", "xl/dialogsheets/", "xl/activex/")
MACRO_ENABLED = b"macroEnabled"
UNREADABLE_ERRORS = (
    InvalidFileException,
    zipfile.BadZipFile,
    KeyError,
    ValueError,
    TypeError,
    IndexError,
    SyntaxError,
    OSError,
)
SAVE_AGAIN = "save the sheet as an .xlsx workbook or as UTF-8 CSV"
NOT_XLSX = f"the file is a zip archive but not an .xlsx workbook: {SAVE_AGAIN}"
OPEN_DOCUMENT = f"an OpenDocument spreadsheet (.ods) is not read here: {SAVE_AGAIN}"
MACROS = "the workbook carries macros or controls ({part}): save it as a plain .xlsx workbook without them"
UNPACKS_LARGE = f"the workbook unpacks to more than {UNPACKED_BYTES_MAX // (1024 * 1024)} MB"
UNREADABLE = f"the workbook could not be read ({{kind}}): {SAVE_AGAIN}"
UNCACHED = (
    "cell {cell} holds the formula {formula} with no value saved: open the workbook in a spreadsheet "
    "program, let it calculate and save it, or replace the formula by its value"
)
ERROR_VALUE = "cell {cell} holds the error {value}: give the value itself"
NO_SHEETS = "the workbook has no sheet of cells"
NO_SHEET = "the workbook has no sheet named {sheet!r}; its sheets are {names}"
LONG_SHEET = f"the sheet runs past row {SHEET_ROWS_READ_MAX:,}; keep the table at its top"
WIDE_ROW = "row {row} has a value in column {column}, past the {most} columns a table may have"


class WorkbookRefused(ValueError):
    pass


def is_workbook(data: bytes) -> bool:
    return data.startswith(ZIP_SIGNATURE)


def workbook_lines(data: bytes, *, sheet: str | None, rows_max: int, columns_max: int) -> list[list[str]]:
    _check_package(data)
    with warnings.catch_warnings(), ExitStack() as held:
        warnings.simplefilter("ignore", UserWarning)
        values = held.enter_context(closing(_opened(data, values_only=True)))
        formulas = held.enter_context(closing(_opened(data, values_only=False)))
        try:
            name = _sheet_name(values, sheet)
            return _read(_sheet(values, name), _sheet(formulas, name), rows_max, columns_max)
        except WorkbookRefused:
            raise
        except UNREADABLE_ERRORS as failed:
            raise WorkbookRefused(UNREADABLE.format(kind=type(failed).__name__)) from None


def _check_package(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if OPEN_DOCUMENT_MARK in names:
                raise WorkbookRefused(OPEN_DOCUMENT)
            if CONTENT_TYPES not in names or WORKBOOK_PART not in names:
                raise WorkbookRefused(NOT_XLSX)
            if sum(entry.file_size for entry in entries) > UNPACKED_BYTES_MAX:
                raise WorkbookRefused(UNPACKS_LARGE)
            _refuse_macros(names, archive.read(CONTENT_TYPES))
    except zipfile.BadZipFile:
        raise WorkbookRefused(UNREADABLE.format(kind="BadZipFile")) from None


def _refuse_macros(names: set[str], content_types: bytes) -> None:
    for name in sorted(names):
        part = next((part for part in MACRO_PARTS if part in name.lower()), None)
        if part is not None:
            raise WorkbookRefused(MACROS.format(part=name))
    if MACRO_ENABLED in content_types:
        raise WorkbookRefused(MACROS.format(part="a macro-enabled workbook"))


def _opened(data: bytes, *, values_only: bool) -> Workbook:
    try:
        return load_workbook(io.BytesIO(data), read_only=True, data_only=values_only, keep_links=False)
    except UNREADABLE_ERRORS as failed:
        raise WorkbookRefused(UNREADABLE.format(kind=type(failed).__name__)) from None


def _sheet_name(book: Workbook, sheet: str | None) -> str:
    names = [worksheet.title for worksheet in book.worksheets]
    if not names:
        raise WorkbookRefused(NO_SHEETS)
    if sheet is None:
        return names[0]
    if sheet not in names:
        raise WorkbookRefused(
            NO_SHEET.format(sheet=sheet, names=", ".join(repr(name) for name in names[:10]))
        )
    return sheet


def _sheet(book: Workbook, name: str) -> Any:
    worksheet = book[name]
    worksheet.reset_dimensions()
    return worksheet


def _read(values: Any, formulas: Any, rows_max: int, columns_max: int) -> list[list[str]]:
    lines: list[list[str]] = []
    for at, row in enumerate(_rows(values, formulas), start=1):
        if at > SHEET_ROWS_READ_MAX:
            raise WorkbookRefused(LONG_SHEET)
        line = _trimmed([_text(shown, written) for shown, written in row])
        if len(line) > columns_max:
            raise WorkbookRefused(WIDE_ROW.format(row=at, column=len(line), most=columns_max))
        if line:
            lines.append(line)
        if len(lines) > rows_max + 1:
            break
    return _padded(lines)


def _rows(values: Any, formulas: Any) -> Iterator[list[tuple[Any, Any]]]:
    for shown, written in zip(values.iter_rows(), formulas.iter_rows(), strict=True):
        yield list(zip(shown, written, strict=True))


def _text(shown: Any, written: Any) -> str:
    if written.data_type == "f" and shown.value is None:
        raise WorkbookRefused(UNCACHED.format(cell=written.coordinate, formula=written.value))
    if shown.data_type == "e":
        raise WorkbookRefused(ERROR_VALUE.format(cell=shown.coordinate, value=shown.value))
    return _shown(shown.value)


def _shown(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return (
            str(int(value))
            if value.is_integer() and abs(value) < 1e15
            else format(value, f".{SIGNIFICANT_DIGITS}g")
        )
    if isinstance(value, datetime):
        return (
            value.date().isoformat()
            if value.time() == time()
            else value.isoformat(sep=" ", timespec="seconds")
        )
    if isinstance(value, date | time):
        return value.isoformat()
    return str(value)


def _trimmed(line: list[str]) -> list[str]:
    end = len(line)
    while end and not line[end - 1].strip():
        end -= 1
    return line[:end]


def _padded(lines: Sequence[list[str]]) -> list[list[str]]:
    if not lines:
        return []
    width = len(lines[0])
    return [line + [""] * (width - len(line)) for line in lines]
