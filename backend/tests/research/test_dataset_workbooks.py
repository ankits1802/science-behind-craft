import io
import zipfile

import pytest
from pydantic import ValidationError

from app.research.dataset_proposals import (
    COLUMNS_MAX,
    ROWS_MAX,
    TABLE_TYPES,
    ParsedTable,
    TableRefused,
    parsed_table,
    record_problems,
    upload_types,
)
from app.research.dataset_workbooks import XLSX_TYPE, is_workbook

from ..workbooks import date_cell, formula, number, text, workbook
from .test_dataset_proposals import proposal

HEADER = [text("district"), text("artisans"), text("double"), text("counted"), text("open"), text("share")]
KACHCHH = [
    text(" Kachchh "),
    number("412"),
    formula("B2*2", "824"),
    date_cell(46000),
    formula("TRUE", "1", kind="b"),
    number("0.25"),
]
BIDAR = [
    text("Bidar"),
    number("640"),
    formula("B3*2", "1280"),
    date_cell(46001),
    formula("FALSE", "0", kind="b"),
    number("0.1"),
]
SAME_AS_CSV = (
    "district,artisans,double,counted,open,share\n"
    "Kachchh,412,824,2025-12-09,TRUE,0.25\n"
    "Bidar,640,1280,2025-12-10,FALSE,0.1\n"
)


def refused(data: bytes, says: str, *, sheet: str | None = None) -> None:
    with pytest.raises(TableRefused, match=says):
        parsed_table(data, sheet=sheet)


def test_an_xlsx_sheet_is_read_into_the_table_its_csv_would_give() -> None:
    read = parsed_table(workbook({"Artisans": [HEADER, KACHCHH, [], BIDAR]}))
    assert read == parsed_table(SAME_AS_CSV.encode())
    assert read == ParsedTable(
        ("district", "artisans", "double", "counted", "open", "share"),
        (
            ("Kachchh", "412", "824", "2025-12-09", "TRUE", "0.25"),
            ("Bidar", "640", "1280", "2025-12-10", "FALSE", "0.1"),
        ),
    )


def test_the_record_s_sheet_is_read_and_without_one_the_first_sheet() -> None:
    notes = [[text("note")], [text("Counted in 2024")]]
    data = workbook({"Notes": notes, "Artisans": [HEADER, KACHCHH]})
    assert parsed_table(data).columns == ("note",)
    assert parsed_table(data, sheet="Artisans").rows[0][0] == "Kachchh"
    refused(data, "no sheet named 'Counts'; its sheets are 'Notes', 'Artisans'", sheet="Counts")


def test_short_rows_are_filled_and_empty_trailing_cells_dropped() -> None:
    rows = [
        [text("district"), text("artisans"), text("note")],
        [text("Kachchh"), number("412")],
        [text("Bidar"), number("640"), text(""), text(" ")],
    ]
    assert parsed_table(workbook({"Sheet1": rows})).rows == (("Kachchh", "412", ""), ("Bidar", "640", ""))


@pytest.mark.parametrize(
    ("extra", "macro_enabled", "says"),
    [
        (
            {"xl/vbaProject.bin": b"\xd0\xcf\x11\xe0"},
            False,
            r"carries macros or controls \(xl/vbaProject.bin\)",
        ),
        ({"xl/macrosheets/sheet1.xml": b"<xm/>"}, False, "carries macros or controls"),
        ({}, True, "carries macros or controls"),
    ],
)
def test_a_workbook_with_macros_is_refused_and_says_so(
    extra: dict[str, bytes], macro_enabled: bool, says: str
) -> None:
    refused(workbook({"Sheet1": [HEADER, KACHCHH]}, extra=extra, macro_enabled=macro_enabled), says)


def test_a_formula_whose_value_was_never_saved_is_refused_by_its_cell_and_formula() -> None:
    unsaved = [text("Kachchh"), number("412"), formula("B2*2", None)]
    refused(
        workbook({"Sheet1": [HEADER[:3], unsaved]}), r"cell C2 holds the formula =B2\*2 with no value saved"
    )


def test_a_formula_with_its_value_saved_is_read_as_that_value() -> None:
    saved = [text("Kachchh"), number("412"), formula("B2*2", "824")]
    assert parsed_table(workbook({"Sheet1": [HEADER[:3], saved]})).rows == (("Kachchh", "412", "824"),)


def test_an_error_value_is_refused() -> None:
    broken = [text("Kachchh"), formula("1/0", "#DIV/0!", kind="e")]
    refused(workbook({"Sheet1": [HEADER[:2], broken]}), "cell B2 holds the error #DIV/0!")


def test_a_value_past_the_last_column_a_table_may_have_is_refused() -> None:
    wide = [text("Kachchh"), *[""] * COLUMNS_MAX, number("1")]
    refused(workbook({"Sheet1": [HEADER[:2], wide]}), f"row 2 has a value in column {COLUMNS_MAX + 2}")


def test_a_workbook_holds_at_most_the_rows_a_csv_may() -> None:
    rows = [[text("n")], *([number("1")] for _ in range(ROWS_MAX + 1))]
    refused(workbook({"Sheet1": rows}), f"1 to {ROWS_MAX} rows")


def test_an_open_document_sheet_a_plain_zip_and_a_sheet_named_for_a_csv_are_refused() -> None:
    ods = io.BytesIO()
    with zipfile.ZipFile(ods, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", "<office:document-content/>")
    refused(ods.getvalue(), r"OpenDocument spreadsheet \(.ods\) is not read here")
    plain = io.BytesIO()
    with zipfile.ZipFile(plain, "w") as archive:
        archive.writestr("notes.txt", "district,artisans")
    refused(plain.getvalue(), "not an .xlsx workbook")
    refused(b"PK\x03\x04 not really a zip", "could not be read")
    refused(SAME_AS_CSV.encode(), "names the sheet 'Artisans', but the file is CSV", sheet="Artisans")


def test_a_table_is_offered_as_csv_or_xlsx_and_a_sheet_belongs_to_a_table_only() -> None:
    assert TABLE_TYPES == ("text/csv", XLSX_TYPE)
    assert upload_types(proposal()) == ["text/csv", XLSX_TYPE]
    assert record_problems(proposal(sheet="Artisans")) == []
    assert is_workbook(workbook({"Sheet1": [HEADER]})) and not is_workbook(SAME_AS_CSV.encode())
    with pytest.raises(ValidationError, match="sheet"):
        proposal(sheet="x" * 32)
