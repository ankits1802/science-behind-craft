from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from pydantic import Field

from .base import ContractModel, HttpsUrl
from .dataset_workbooks import (
    SHEET_NAME_MAX_CHARS,
    WORKBOOK_TYPES,
    WorkbookRefused,
    is_workbook,
    workbook_lines,
)
from .datasets import DATASET_CODE_PATTERN, DOI_PATTERN, SHA256_PATTERN
from .licences import open_licence
from .map_layer_proposals import LAYER_TYPES, MapLayerPlan, layer_problems

__all__ = [
    "CELL_MAX_CHARS",
    "COLUMNS_MAX",
    "DATASET_UPLOAD_LIFETIME",
    "DATASET_UPLOAD_ROUTE",
    "ROWS_MAX",
    "SLOT_PREFIX",
    "TABLE_BYTES_MAX",
    "TABLE_TYPES",
    "DatasetProposal",
    "DatasetReply",
    "DatasetUploadStart",
    "ParsedTable",
    "TableRefused",
    "parsed_table",
    "record_problems",
    "upload_types",
    "upload_url",
]

TABLE_BYTES_MAX = 5 * 1024 * 1024
ROWS_MAX = 20_000
COLUMNS_MAX = 60
CELL_MAX_CHARS = 500
TABLE_TYPES = ("text/csv", *WORKBOOK_TYPES)
SLOT_PREFIX = "kvds_"
DATASET_UPLOAD_ROUTE = "/api/dataset-uploads"
DATASET_UPLOAD_LIFETIME = timedelta(minutes=30)
UTF8_BOM = "﻿"


class DatasetProposal(ContractModel):
    code: str = Field(pattern=DATASET_CODE_PATTERN, min_length=3, max_length=80)
    title: str = Field(min_length=3, max_length=300)
    publisher: str = Field(min_length=2, max_length=300)
    edition: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=120)
    period: str = Field(min_length=1, max_length=120)
    native_resolution: str = Field(min_length=1, max_length=120)
    crs: str = Field(min_length=1, max_length=120)
    licence: str = Field(min_length=2, max_length=200)
    licence_url: HttpsUrl
    attribution: str = Field(min_length=2, max_length=1000)
    redistributable: bool
    citation: str = Field(min_length=10, max_length=1000)
    doi: str | None = Field(default=None, pattern=DOI_PATTERN)
    landing_url: HttpsUrl
    url: HttpsUrl
    sha256: str = Field(pattern=SHA256_PATTERN)
    sheet: str | None = Field(default=None, min_length=1, max_length=SHEET_NAME_MAX_CHARS)
    layer: MapLayerPlan | None = None


class DatasetUploadStart(ContractModel):
    upload_url: str
    upload_method: Literal["PUT"] = "PUT"
    upload_types: list[str] = Field(default_factory=lambda: list(TABLE_TYPES))
    upload_max_bytes: int = TABLE_BYTES_MAX
    expires_at: datetime


class DatasetReply(ContractModel):
    schema_version: Literal[1] = 1
    code: str
    outcome: Literal["UPLOAD", "STORED", "REFUSED"]
    message: str
    upload: DatasetUploadStart | None = None
    columns: list[str] = Field(default_factory=list)
    rows: int = Field(default=0, ge=0)
    features: int = Field(default=0, ge=0)


@dataclass(frozen=True)
class ParsedTable:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


class TableRefused(ValueError):
    pass


def record_problems(proposal: DatasetProposal) -> list[str]:
    problems = []
    if not (open_licence(proposal.licence) or open_licence(proposal.licence_url)):
        problems.append(
            f"the licence {proposal.licence!r} is not one the gates read as open: give a public-domain, CC0, "
            "PDDL, CC BY or CC BY-SA licence with its address"
        )
    if not proposal.redistributable:
        problems.append("a contributed dataset is one its licence lets anyone redistribute")
    if proposal.doi is not None and proposal.doi not in proposal.citation:
        problems.append(f"the citation names its DOI {proposal.doi}")
    if proposal.layer is not None:
        problems += layer_problems(proposal.crs, proposal.layer)
    if proposal.layer is not None and proposal.sheet is not None:
        problems.append(
            "a sheet names the workbook sheet a table is read from; a map layer is GeoJSON and has none"
        )
    return problems


def upload_types(proposal: DatasetProposal) -> list[str]:
    return list(LAYER_TYPES if proposal.layer is not None else TABLE_TYPES)


def parsed_table(data: bytes, *, sheet: str | None = None) -> ParsedTable:
    if not data or len(data) > TABLE_BYTES_MAX:
        raise TableRefused(
            f"a table is 1 byte to {TABLE_BYTES_MAX // (1024 * 1024)} MB of CSV or an .xlsx workbook"
        )
    if not is_workbook(data):
        return _table(_csv_lines(data, sheet))
    try:
        return _table(workbook_lines(data, sheet=sheet, rows_max=ROWS_MAX, columns_max=COLUMNS_MAX))
    except WorkbookRefused as refused:
        raise TableRefused(str(refused)) from None


def _csv_lines(data: bytes, sheet: str | None) -> list[list[str]]:
    if sheet is not None:
        raise TableRefused(f"the record names the sheet {sheet!r}, but the file is CSV, which has none")
    try:
        text = data.decode("utf-8").removeprefix(UTF8_BOM)
    except UnicodeDecodeError:
        raise TableRefused("a table is UTF-8 CSV or an .xlsx workbook") from None
    return list(csv.reader(io.StringIO(text, newline="")))


def _table(lines: list[list[str]]) -> ParsedTable:
    if len(lines) < 2:
        raise TableRefused("a table has a header row and at least one row of values")
    header = tuple(cell.strip() for cell in lines[0])
    _check_header(header)
    rows = tuple(
        tuple(cell.strip() for cell in line) for line in lines[1:] if any(cell.strip() for cell in line)
    )
    if not rows or len(rows) > ROWS_MAX:
        raise TableRefused(f"a table has 1 to {ROWS_MAX} rows of values")
    for at, row in enumerate(rows, start=1):
        if len(row) != len(header):
            raise TableRefused(f"row {at} has {len(row)} cells, and the header names {len(header)} columns")
        if any(len(cell) > CELL_MAX_CHARS for cell in row):
            raise TableRefused(f"row {at} holds a cell of more than {CELL_MAX_CHARS} characters")
    return ParsedTable(header, rows)


def _check_header(header: tuple[str, ...]) -> None:
    if not header or len(header) > COLUMNS_MAX:
        raise TableRefused(f"a table has 1 to {COLUMNS_MAX} columns")
    if any(not name or len(name) > CELL_MAX_CHARS for name in header):
        raise TableRefused("every column of the header row has a name")
    if len(set(header)) != len(header):
        raise TableRefused("every column of the header row has a name of its own")


def upload_url(api_origin: str, token: str) -> str:
    return f"{api_origin.rstrip('/')}{DATASET_UPLOAD_ROUTE}/{token}"
