import hashlib
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EnvDataset, SuppliedSource
from app.services import dataset_proposals as proposals, supplied_sources
from app.services.malware_scan import MalwareFound, ScannerDown

from ..upload_scanners import EICAR, EICAR_SIGNATURE, ScriptedScanner
from ..workbooks import number, text, workbook
from .test_dataset_proposals_db import CODE, CSV, NOW, person, record, session
from .test_supplied_sources_db import PASSAGE, supply

__all__ = ["session"]

pytestmark = pytest.mark.db

XLSX = workbook(
    {
        "Notes": [[text("note")], [text("Counted in 2024")]],
        "Artisans": [
            [text("district"), text("artisans")],
            [text("Kachchh"), number("1200")],
            [text("Bidar"), number("640")],
        ],
    }
)
INFECTED = CSV + EICAR.encode("ascii") + b",1\n"
WORDS = " ".join([PASSAGE] * 3)


async def slot_for(session: AsyncSession, data: bytes, **changes: str) -> str:
    proposal = record(sha256=hashlib.sha256(data).hexdigest(), **changes)
    return (await proposals.issue_dataset_slot(session, await person(session), proposal, now=NOW)).token


async def dataset_held(session: AsyncSession) -> bool:
    return await session.scalar(select(EnvDataset.id).where(EnvDataset.code == CODE)) is not None


async def test_an_xlsx_sheet_named_by_the_record_is_stored_as_the_table_its_csv_gives(
    session: AsyncSession,
) -> None:
    token = await slot_for(session, XLSX, sheet="Artisans", url="https://example.org/artisans.xlsx")
    made = await proposals.fill_dataset_slot(session, token, XLSX, now=NOW + timedelta(minutes=5))
    assert made.table is not None
    assert (made.table.columns, made.table.rows) == (
        ("district", "artisans"),
        (("Kachchh", "1200"), ("Bidar", "640")),
    )


async def test_a_table_carrying_the_eicar_file_is_refused_and_nothing_is_stored(
    session: AsyncSession, upload_scanner: ScriptedScanner
) -> None:
    token = await slot_for(session, INFECTED)
    with pytest.raises(MalwareFound, match=EICAR_SIGNATURE):
        await proposals.fill_dataset_slot(session, token, INFECTED, now=NOW + timedelta(minutes=5))
    assert not await dataset_held(session)
    assert upload_scanner.scanned == [INFECTED]


async def test_a_table_sent_while_the_scanner_is_down_is_refused_and_its_slot_stays_open(
    session: AsyncSession, upload_scanner: ScriptedScanner
) -> None:
    token = await slot_for(session, CSV)
    upload_scanner.down = True
    with pytest.raises(ScannerDown):
        await proposals.fill_dataset_slot(session, token, CSV, now=NOW + timedelta(minutes=5))
    assert not await dataset_held(session)
    upload_scanner.down = False
    made = await proposals.fill_dataset_slot(session, token, CSV, now=NOW + timedelta(minutes=6))
    assert made.table is not None and made.table.rows == (("Kachchh", "1200"), ("Bidar", "640"))


async def test_a_supplied_file_is_scanned_before_its_text_is_read(
    session: AsyncSession, upload_scanner: ScriptedScanner
) -> None:
    researcher = await person(session)
    made = await supply(session, researcher, passages=[], upload="text")
    assert made.slot_token is not None
    with pytest.raises(MalwareFound):
        await supplied_sources.fill_supplied_slot(session, made.slot_token, EICAR.encode("ascii"), now=NOW)
    row = await session.get(SuppliedSource, made.row.id)
    assert row is not None and (row.state, row.text) == ("AWAITING_FILE", None)
    upload_scanner.down = True
    with pytest.raises(ScannerDown):
        await supplied_sources.fill_supplied_slot(session, made.slot_token, PASSAGE.encode(), now=NOW)
    upload_scanner.down = False
    filled = await supplied_sources.fill_supplied_slot(session, made.slot_token, PASSAGE.encode(), now=NOW)
    assert filled.state == "READY"


async def supplied_rows(session: AsyncSession) -> int:
    return len((await session.scalars(select(SuppliedSource.id))).all())


async def test_words_supplied_in_the_call_are_scanned_whole_before_they_are_kept(
    session: AsyncSession, upload_scanner: ScriptedScanner
) -> None:
    made = await supply(session, await person(session), passages=[], text=WORDS)
    assert upload_scanner.scanned == [WORDS.encode("utf-8")]
    assert (made.row.state, made.row.text) == ("READY", WORDS)


async def test_words_carrying_the_eicar_test_file_are_refused_and_nothing_is_kept(
    session: AsyncSession,
) -> None:
    researcher = await person(session)
    before = await supplied_rows(session)
    with pytest.raises(MalwareFound, match=EICAR_SIGNATURE):
        await supply(session, researcher, passages=[], text=f"{WORDS} {EICAR}")
    assert await supplied_rows(session) == before


async def test_words_supplied_while_the_scanner_is_down_are_refused_and_nothing_is_kept(
    session: AsyncSession, upload_scanner: ScriptedScanner
) -> None:
    researcher = await person(session)
    before = await supplied_rows(session)
    upload_scanner.down = True
    with pytest.raises(ScannerDown):
        await supply(session, researcher)
    assert await supplied_rows(session) == before
