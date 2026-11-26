from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping, Sequence
from xml.sax.saxutils import escape

__all__ = ["Cell", "date_cell", "formula", "number", "text", "workbook"]

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
SHEET_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
MAIN_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
MACRO_MAIN_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
STYLES = (
    f'<styleSheet xmlns="{MAIN}"><fonts count="1"><font/></fonts><fills count="1"><fill><patternFill '
    'patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/>'
    '</cellStyleXfs><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14" applyNumberFormat="1"/></cellXfs>'
    "</styleSheet>"
)

Cell = str


def text(value: str) -> Cell:
    return f'<c t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def number(value: str) -> Cell:
    return f"<c><v>{value}</v></c>"


def formula(expression: str, cached: str | None, *, kind: str = "") -> Cell:
    typed = f' t="{kind}"' if kind else ""
    saved = "" if cached is None else f"<v>{escape(cached)}</v>"
    return f"<c{typed}><f>{escape(expression)}</f>{saved}</c>"


def date_cell(serial: int) -> Cell:
    return f'<c s="1"><v>{serial}</v></c>'


def workbook(
    sheets: Mapping[str, Sequence[Sequence[Cell]]],
    *,
    extra: Mapping[str, bytes] | None = None,
    macro_enabled: bool = False,
) -> bytes:
    names = list(sheets)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(names), macro_enabled=macro_enabled))
        archive.writestr("_rels/.rels", _relations([("officeDocument", "xl/workbook.xml")]))
        archive.writestr("xl/workbook.xml", _workbook(names))
        parts = [("worksheet", f"worksheets/sheet{at}.xml") for at in range(1, len(names) + 1)]
        archive.writestr("xl/_rels/workbook.xml.rels", _relations([*parts, ("styles", "styles.xml")]))
        archive.writestr("xl/styles.xml", STYLES)
        for at, name in enumerate(names, start=1):
            archive.writestr(f"xl/worksheets/sheet{at}.xml", _sheet(sheets[name]))
        for path, data in (extra or {}).items():
            archive.writestr(path, data)
    return buffer.getvalue()


def _content_types(sheets: int, *, macro_enabled: bool) -> str:
    main = MACRO_MAIN_TYPE if macro_enabled else MAIN_TYPE
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{at}.xml" ContentType="{SHEET_TYPE}"/>'
        for at in range(1, sheets + 1)
    )
    return (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" ContentType="{main}"/>{overrides}</Types>'
    )


def _relations(targets: Sequence[tuple[str, str]]) -> str:
    listed = "".join(
        f'<Relationship Id="rId{at}" Type="{RELATIONS}/{kind}" Target="{target}"/>'
        for at, (kind, target) in enumerate(targets, start=1)
    )
    return f'<Relationships xmlns="{PACKAGE}">{listed}</Relationships>'


def _workbook(names: Sequence[str]) -> str:
    listed = "".join(
        f'<sheet name="{escape(name)}" sheetId="{at}" r:id="rId{at}"/>'
        for at, name in enumerate(names, start=1)
    )
    return f'<workbook xmlns="{MAIN}" xmlns:r="{RELATIONS}"><sheets>{listed}</sheets></workbook>'


def _sheet(rows: Sequence[Sequence[Cell]]) -> str:
    lines = "".join(
        f'<row r="{at}">{"".join(_placed(cell, at, column) for column, cell in enumerate(row))}</row>'
        for at, row in enumerate(rows, start=1)
        if row
    )
    return f'<worksheet xmlns="{MAIN}"><sheetData>{lines}</sheetData></worksheet>'


def _placed(cell: Cell, row: int, column: int) -> str:
    if not cell:
        return ""
    return cell.replace("<c", f'<c r="{_column(column)}{row}"', 1)


def _column(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
