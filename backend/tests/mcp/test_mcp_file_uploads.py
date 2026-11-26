import base64
import hashlib
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_dataset_tools, mcp_picture_files, mcp_studio_sources
from app.api.mcp_tools import TOOLS, ToolContext, answered_whole
from app.core.config import get_settings
from app.models import DatasetUpload, EnvDataset, ImageContribution, UploadLink, User
from app.research.upload_links import SlotCraft, SlotDeclaration, UploadSlot, slot_upload_url
from app.services import upload_links
from app.services.dataset_proposals import IssuedSlot
from app.services.supplied_sources import Supplied

from .modern_client import FILES, FORMS, error_of, legacy, modern, result_of, tool_call
from .test_mcp_studio_tools import ACCESS, API, IDENTITY, USER_ID, Endpoints, context, lookups, supplied_row
from .test_proposal_limits import DATASET

__all__ = ["lookups"]

EXPIRES = datetime.now(UTC) + timedelta(minutes=30)
PDF = {"id": "file-1", "name": "Mordant printing.pdf", "mimeType": "application/pdf", "size": 48_213}
PHOTO = {"id": "photo-1", "name": "block.jpg", "mimeType": "image/jpeg", "size": 812_004}
CSV_BYTES = b"district,artisans\nKachchh,412\n"
CSV = {
    "id": "table-1",
    "name": "artisans.csv",
    "mimeType": "text/csv",
    "size": len(CSV_BYTES),
    "digest": {
        "algorithm": "sha-256",
        "value": base64.urlsafe_b64encode(hashlib.sha256(CSV_BYTES).digest()).decode().rstrip("="),
    },
}
SLOT_URL = f"{API}/api/knowledge/supplied-sources/slots/kvss_token"
LINK_ID = uuid.UUID(int=901)
CONTRIBUTION_ID = uuid.UUID(int=902)
UPLOAD_ID = uuid.UUID(int=903)
DATASET_ID = uuid.UUID(int=904)
FACT = uuid.UUID(int=21)
DECLARATION = {"origin": "DRAWING", "rights_confirmed": True, "terms_version": "2026-11-19"}
WORDS = {
    "caption": "The resist paste on the block",
    "alt_text": "A drawing of a carved block coated in grey paste",
}


class StoredSession:
    def __init__(self, *rows: Any) -> None:
        self.rows = {(type(row), row.id): row for row in rows}
        self.ended: list[str] = []

    async def get(self, model: type, ident: uuid.UUID) -> Any:
        return self.rows.get((model, ident))

    async def commit(self) -> None:
        self.ended.append("commit")

    async def rollback(self) -> None:
        self.ended.append("rollback")


def sending(*rows: Any) -> ToolContext:
    return replace(context(), session=StoredSession(*rows))  # type: ignore[arg-type]


def file_call(
    name: str, arguments: dict[str, Any], *, capabilities: dict[str, Any] = FILES, **extra: Any
) -> dict[str, Any]:
    return modern("tools/call", tool_call(name, arguments, **extra), capabilities=capabilities)


async def first_and_retry(
    name: str, arguments: dict[str, Any], tool_context: ToolContext
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = await result_of(file_call(name, arguments), tool_context)
    assert first["resultType"] == "upload_required", first
    again = await result_of(file_call(name, arguments, requestState=first["requestState"]), tool_context)
    return first, again


def supplying(monkeypatch: pytest.MonkeyPatch, state: str = "READY") -> list[Any]:
    drafts: list[Any] = []

    async def supply(session: Any, user: User, draft: Any, *, lookup: Any, now: datetime) -> Supplied:
        drafts.append(draft)
        waiting = supplied_row("AWAITING_FILE")
        waiting.slotExpiresAt = EXPIRES
        return Supplied(row=waiting, slot_token="kvss_token")

    async def own(session: Any, user: User, supplied_id: uuid.UUID) -> Any:
        assert user.id == USER_ID
        return supplied_row(state)

    monkeypatch.setattr(mcp_studio_sources.supplied_sources, "supply_source", supply)
    monkeypatch.setattr(mcp_studio_sources.supplied_sources, "own_supplied", own)
    return drafts


async def test_a_client_with_the_extension_is_offered_a_file_argument_on_the_three_tools() -> None:
    tools = {
        tool["name"]: tool
        for tool in (await result_of(modern("tools/list", capabilities=FILES), context()))["tools"]
    }
    source = tools["supply_source"]["inputSchema"]["properties"]["file"]
    assert source["x-mcp-file"] == {
        "accept": ["application/pdf", "text/plain", ".pdf", ".txt"],
        "maxSize": 20 * 1024 * 1024,
    }
    assert source["required"] == ["id", "mimeType", "size"]
    photos = tools["give_pictures"]["inputSchema"]["properties"]["files"]
    assert photos["type"] == "array" and photos["items"]["x-mcp-file"]["maxSize"] == 10 * 1024 * 1024
    table = tools["propose_dataset"]["inputSchema"]["properties"]["file"]["x-mcp-file"]
    assert table == {
        "accept": ["text/csv", "application/geo+json", ".csv", ".geojson"],
        "maxSize": 5 * 1024 * 1024,
    }
    assert {name for name, tool in TOOLS.items() if tool.files is not None} == {
        "supply_source",
        "give_pictures",
        "propose_dataset",
    }


@pytest.mark.parametrize("message", [legacy("tools/list"), modern("tools/list", capabilities=FORMS)])
async def test_a_client_without_the_extension_sees_today_s_arguments(message: dict[str, Any]) -> None:
    tools = {tool["name"]: tool for tool in (await result_of(message, context()))["tools"]}
    assert "file" not in tools["supply_source"]["inputSchema"]["properties"]
    assert "files" not in tools["give_pictures"]["inputSchema"]["properties"]
    assert "file" not in tools["propose_dataset"]["inputSchema"]["properties"]


async def test_an_uploaded_pdf_reaches_supply_source_through_its_private_slot(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    drafts = supplying(monkeypatch)
    tool_context = sending()
    first, again = await first_and_retry(
        "supply_source", {"identity": IDENTITY, "access": ACCESS, "file": PDF}, tool_context
    )
    (target,) = first["uploads"]
    assert target == {
        "fileId": "file-1",
        "url": SLOT_URL,
        "method": "PUT",
        "headers": {"Content-Type": "application/octet-stream"},
        "credentials": "omit",
        "expiresAt": target["expiresAt"],
    }
    assert "content" not in first and len(drafts) == 1 and drafts[0].upload == "pdf"
    assert again["isError"] is False and again["structuredContent"]["state"] == "READY" and len(drafts) == 1
    assert tool_context.session.ended == ["commit", "commit"]  # type: ignore[attr-defined]


async def test_a_pdf_that_never_arrived_runs_nothing(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    supplying(monkeypatch, state="AWAITING_FILE")
    _, again = await first_and_retry(
        "supply_source", {"identity": IDENTITY, "access": ACCESS, "file": PDF}, sending()
    )
    assert again["isError"] is True and "has not arrived" in again["content"][0]["text"]


@pytest.mark.parametrize(
    ("file", "said"),
    [
        ({**PDF, "name": "notes.zip", "mimeType": "application/zip"}, "this tool takes application/pdf"),
        ({**PDF, "size": 30 * 1024 * 1024}, "at most 20,971,520 bytes"),
        ({**PDF, "data": "JVBERi0xLjQ="}, "not taken inside the call"),
        ({**PDF, "size": 0}, "is empty"),
    ],
)
async def test_a_refused_type_size_or_way_is_refused_with_its_reason(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any], file: dict[str, Any], said: str
) -> None:
    drafts = supplying(monkeypatch)
    refused = await result_of(
        file_call("supply_source", {"identity": IDENTITY, "access": ACCESS, "file": file}), sending()
    )
    assert refused["isError"] is True and said in refused["content"][0]["text"] and drafts == []


async def test_a_file_sent_by_a_client_that_did_not_declare_uploads_is_refused_with_the_capability(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    drafts = supplying(monkeypatch)
    message = file_call(
        "supply_source", {"identity": IDENTITY, "access": ACCESS, "file": PDF}, capabilities=FORMS
    )
    refused = await error_of(message, sending())
    assert refused["code"] == -32021 and drafts == []
    assert refused["data"]["requiredCapabilities"] == {
        "extensions": {"io.modelcontextprotocol/files": {"upload": {}}}
    }
    assert answered_whole(message) and not answered_whole(
        legacy("tools/call", tool_call("supply_source", {}))
    )


async def test_switched_off_uploads_list_no_file_argument_and_take_no_file(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    monkeypatch.setattr(get_settings(), "mcp_file_uploads_enabled", False)
    drafts = supplying(monkeypatch)
    tools = {
        tool["name"]: tool
        for tool in (await result_of(modern("tools/list", capabilities=FILES), context()))["tools"]
    }
    assert "file" not in tools["supply_source"]["inputSchema"]["properties"]
    refused = await result_of(
        file_call("supply_source", {"identity": IDENTITY, "access": ACCESS, "file": PDF}), sending()
    )
    assert refused["isError"] is True and "takes no files" in refused["content"][0]["text"] and drafts == []


async def test_a_client_without_the_extension_keeps_today_s_upload_slot(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    supplying(monkeypatch)
    content = (
        await result_of(
            file_call(
                "supply_source", {"identity": IDENTITY, "access": ACCESS, "upload": "pdf"}, capabilities=FORMS
            ),
            sending(),
        )
    )["structuredContent"]
    assert content["upload"]["uploadUrl"] == SLOT_URL


def issuing(monkeypatch: pytest.MonkeyPatch) -> list[SlotDeclaration | None]:
    seen: list[SlotDeclaration | None] = []

    async def start(
        session: Any, user: User, slot: UploadSlot, declaration: SlotDeclaration | None, *, now: datetime
    ) -> upload_links.IssuedLink:
        seen.append(declaration)
        return upload_links.IssuedLink(
            link_token="kvup_pg_link-token",
            slot_token=None if declaration is None else "kvup_sl_slot-token",
            expires_at=EXPIRES,
            craft=SlotCraft(slug="Kutch-Ajrakh", name="Kutch Ajrakh"),
            stage=None,
            facts=[],
            link_id=LINK_ID,
        )

    monkeypatch.setattr(upload_links, "start_upload", start)
    monkeypatch.setattr(mcp_picture_files, "endpoints_or_none", lambda: Endpoints(API))
    return seen


def photographs(**changes: Any) -> dict[str, Any]:
    picture = {"upload": True, "claim_ids": [str(FACT)], **WORDS}
    return {
        "craft_slug": "Kutch-Ajrakh",
        "declaration": DECLARATION,
        "confirmation": "Yes, I drew it and share it on these terms.",
        "pictures": [picture],
        "files": [PHOTO],
    } | changes


async def test_an_uploaded_photograph_reaches_give_pictures_declared_and_screened_at_its_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = issuing(monkeypatch)
    link = UploadLink(id=LINK_ID, userId=USER_ID, contributionId=CONTRIBUTION_ID)
    received = ImageContribution(id=CONTRIBUTION_ID, status="PENDING")
    first, again = await first_and_retry("give_pictures", photographs(), sending(link, received))
    (target,) = first["uploads"]
    assert (target["fileId"], target["url"]) == ("photo-1", slot_upload_url(API, "kvup_sl_slot-token"))
    (declaration,) = seen
    assert declaration is not None and (declaration.origin, declaration.caption) == (
        "DRAWING",
        WORDS["caption"],
    )
    reply = again["structuredContent"]
    assert (reply["given"], reply["uploads"], len(seen)) == (1, [], 1)
    (picture,) = reply["pictures"]
    assert (picture["position"], picture["contributionId"], picture["status"]) == (
        1,
        str(CONTRIBUTION_ID),
        "PENDING",
    )


@pytest.mark.parametrize(
    ("changes", "said"),
    [
        ({"declaration": None, "confirmation": None}, "need the declaration"),
        ({"files": [PHOTO, {**PHOTO, "id": "photo-2"}]}, "give one file for each picture"),
        (
            {"files": [{**PHOTO, "name": "notes.pdf", "mimeType": "application/pdf"}]},
            "this tool takes image/",
        ),
    ],
)
async def test_a_photograph_without_its_declaration_or_its_picture_is_refused(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, Any], said: str
) -> None:
    seen = issuing(monkeypatch)
    refused = await result_of(file_call("give_pictures", photographs(**changes)), sending())
    assert refused["isError"] is True and said in refused["content"][0]["text"] and seen == []


async def test_a_photograph_that_failed_its_screening_gives_no_picture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issuing(monkeypatch)
    unfilled = UploadLink(id=LINK_ID, userId=USER_ID, contributionId=None)
    _, again = await first_and_retry("give_pictures", photographs(), sending(unfilled))
    assert again["isError"] is True and "has not arrived" in again["content"][0]["text"]


def dataset_slots(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    issued: list[Any] = []

    class Fetching:
        async def __aenter__(self) -> Fetching:
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

    async def problems(session: Any, fetcher: Any, proposal: Any) -> list[str]:
        return []

    async def issue(session: Any, user: User, proposal: Any, *, now: datetime) -> IssuedSlot:
        issued.append(proposal)
        return IssuedSlot(token="kvds_token", expires_at=EXPIRES, upload_id=UPLOAD_ID)

    monkeypatch.setattr(mcp_dataset_tools, "proposal_fetcher", Fetching)
    monkeypatch.setattr(mcp_dataset_tools, "proposal_problems", problems)
    monkeypatch.setattr(mcp_dataset_tools, "issue_dataset_slot", issue)
    monkeypatch.setattr(mcp_dataset_tools, "endpoints_or_none", lambda: Endpoints(API))
    return issued


async def test_an_uploaded_csv_reaches_propose_dataset_and_its_table_is_checked_at_its_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued = dataset_slots(monkeypatch)
    proposal = {**DATASET, "sha256": hashlib.sha256(CSV_BYTES).hexdigest()}
    upload = DatasetUpload(id=UPLOAD_ID, userId=USER_ID, datasetId=DATASET_ID, record=proposal)
    stored = EnvDataset(id=DATASET_ID, code=DATASET["code"])
    first, again = await first_and_retry(
        "propose_dataset", {"proposal": proposal, "file": CSV}, sending(upload, stored)
    )
    assert first["uploads"][0]["url"] == f"{API}/api/dataset-uploads/kvds_token" and len(issued) == 1
    reply = again["structuredContent"]
    assert (reply["code"], reply["outcome"], len(issued)) == (DATASET["code"], "STORED", 1)


async def test_a_csv_that_is_not_the_declared_file_is_refused_before_any_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued = dataset_slots(monkeypatch)
    refused = await result_of(file_call("propose_dataset", {"proposal": DATASET, "file": CSV}), sending())
    assert refused["isError"] is True and "SHA-256" in refused["content"][0]["text"] and issued == []
    spreadsheet = {
        **CSV,
        "name": "artisans.xlsx",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    typed = await result_of(
        file_call("propose_dataset", {"proposal": DATASET, "file": spreadsheet}), sending()
    )
    assert typed["isError"] is True and "text/csv" in typed["content"][0]["text"]


async def test_a_retry_on_another_account_or_with_other_arguments_is_refused(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    supplying(monkeypatch)
    arguments = {"identity": IDENTITY, "access": ACCESS, "file": PDF}
    first = await result_of(file_call("supply_source", arguments), sending())
    changed = file_call(
        "supply_source", {**arguments, "file": {**PDF, "size": 48_214}}, requestState=first["requestState"]
    )
    assert (await error_of(changed, sending()))["code"] == -32602
    other = User(id=uuid.uuid4(), name="Someone", email="else@example.org", role="RESEARCHER", tokenVersion=0)
    stranger = file_call("supply_source", arguments, requestState=first["requestState"])
    assert (await error_of(stranger, replace(sending(), user=other)))["code"] == -32602
