import base64
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.mcp_headers import header_value
from app.api.mcp_protocol import SERVER_INSTRUCTIONS
from app.api.routes.mcp import mcp_enabled
from app.core.config import get_settings
from app.core.db import get_session
from app.main import create_app

from .modern_client import VERSION, bare_context, error_of, legacy, modern, result_of, tool_call

EXTENSIONS = {
    "io.modelcontextprotocol/skills": {},
    "io.modelcontextprotocol/tasks": {},
    "io.modelcontextprotocol/files": {"upload": {}},
}
SERVER_INFO = "io.modelcontextprotocol/serverInfo"


async def no_session() -> AsyncIterator[Any]:
    yield None


def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    app.dependency_overrides[mcp_enabled] = lambda: None
    return TestClient(app)


def headers(method: str, name: str | None = None, version: str = VERSION) -> dict[str, str]:
    sent = {"mcp-protocol-version": version, "mcp-method": method}
    return sent if name is None else {**sent, "mcp-name": name}


async def test_discover_names_the_versions_the_three_extensions_and_the_instructions() -> None:
    result = await result_of(modern("server/discover"), bare_context())
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"]
    assert result["capabilities"] == {"tools": {}, "prompts": {}, "resources": {}, "extensions": EXTENSIONS}
    assert result["instructions"] == SERVER_INSTRUCTIONS
    assert (result["ttlMs"], result["cacheScope"]) == (300_000, "public")
    assert result["_meta"][SERVER_INFO]["name"] == "kalavigyan"


async def test_switching_file_uploads_off_takes_the_files_extension_out_of_discover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "mcp_file_uploads_enabled", False)
    result = await result_of(modern("server/discover"), bare_context())
    assert set(result["capabilities"]["extensions"]) == {
        "io.modelcontextprotocol/skills",
        "io.modelcontextprotocol/tasks",
    }


@pytest.mark.parametrize("asked", ["2025-11-25", "2026-07-28", "1999-01-01"])
async def test_a_client_that_initializes_still_agrees_the_2025_11_25_handshake(asked: str) -> None:
    result = await result_of(
        legacy("initialize", {"protocolVersion": asked, "capabilities": {}}), bare_context()
    )
    assert result["protocolVersion"] == "2025-11-25"
    assert "extensions" not in result["capabilities"] and "resultType" not in result


async def test_discover_skills_and_tasks_are_methods_of_the_new_protocol_only() -> None:
    for method in ("server/discover", "skills/list", "tasks/get"):
        assert (await error_of(legacy(method), bare_context()))["code"] == -32601, method


async def test_a_new_protocol_request_carries_its_capabilities_and_a_version_the_server_speaks() -> None:
    message = modern("tools/list")
    del message["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"]
    missing = await error_of(message, bare_context())
    assert missing["code"] == -32602 and "clientCapabilities" in missing["message"]
    later = modern("tools/list")
    later["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2030-01-01"
    unknown = await error_of(later, bare_context())
    assert (unknown["code"], unknown["data"]["requested"]) == (-32022, "2030-01-01")
    assert "2026-07-28" in unknown["data"]["supported"] and "2025-11-25" in unknown["data"]["supported"]


async def test_every_new_protocol_result_names_its_type_and_cacheable_ones_their_freshness() -> None:
    listed = await result_of(modern("tools/list"), bare_context())
    assert (listed["resultType"], listed["ttlMs"], listed["cacheScope"]) == ("complete", 300_000, "private")
    assert {tool["name"] for tool in listed["tools"]} >= {"find_crafts", "get_page", "preview_page"}
    resources = await result_of(modern("resources/list"), bare_context())
    assert (resources["resultType"], resources["cacheScope"]) == ("complete", "public")
    pinged = await result_of(modern("ping"), bare_context())
    assert pinged["resultType"] == "complete" and "ttlMs" not in pinged
    called = await result_of(modern("tools/call", tool_call("get_page", {})), bare_context())
    assert (called["resultType"], called["isError"]) == ("complete", False) and "ttlMs" not in called
    assert called["_meta"][SERVER_INFO]["version"]


async def test_the_old_protocol_s_results_are_unchanged() -> None:
    listed = await result_of(legacy("tools/list"), bare_context())
    assert "resultType" not in listed and "ttlMs" not in listed and "_meta" not in listed
    called = await result_of(legacy("tools/call", tool_call("get_page", {})), bare_context())
    assert "resultType" not in called and "_meta" not in called


async def test_a_missing_resource_is_invalid_params_on_the_new_protocol_and_32002_on_the_old() -> None:
    asked = {"uri": "kalavigyan://nowhere.md"}
    assert (await error_of(modern("resources/read", asked), bare_context()))["code"] == -32602
    assert (await error_of(legacy("resources/read", asked), bare_context()))["code"] == -32002


def test_a_name_header_is_plain_or_base64_and_anything_else_is_refused() -> None:
    encoded = "=?base64?" + base64.b64encode("Kutch Ajrakh, कच्छ".encode()).decode() + "?="
    assert header_value(encoded) == "Kutch Ajrakh, कच्छ"
    assert header_value("get_page") == "get_page"
    assert header_value(" padded ") is None
    assert header_value("=?base64?not base64?=") is None


def test_the_route_answers_a_new_protocol_request_whose_headers_match_its_body() -> None:
    answered = client().post("/api/mcp", json=modern("server/discover"), headers=headers("server/discover"))
    assert answered.status_code == 200 and answered.json()["result"]["resultType"] == "complete"
    call = modern("tools/call", tool_call("get_page", {}))
    named = client().post("/api/mcp", json=call, headers=headers("tools/call", "get_page"))
    assert named.status_code == 200 and named.json()["result"]["isError"] is False
    encoded = "=?base64?" + base64.b64encode(b"get_page").decode() + "?="
    decoded = client().post("/api/mcp", json=call, headers=headers("tools/call", encoded))
    assert decoded.status_code == 200


def test_the_route_refuses_missing_or_mismatched_headers_with_400_and_header_mismatch() -> None:
    call = modern("tools/call", tool_call("get_page", {}))
    for sent in (
        {"mcp-protocol-version": VERSION, "mcp-name": "get_page"},
        headers("tools/call"),
        headers("tools/call", "find_crafts"),
        headers("tools/list", "get_page"),
    ):
        refused = client().post("/api/mcp", json=call, headers=sent)
        assert refused.status_code == 400, sent
        assert refused.json()["error"]["code"] == -32020, sent


def test_the_route_answers_an_unknown_method_404_and_an_unknown_version_400_with_the_versions() -> None:
    unknown = client().post("/api/mcp", json=modern("tools/dance"), headers=headers("tools/dance"))
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == -32601
    stale = client().post(
        "/api/mcp", json=legacy("tools/list"), headers={"mcp-protocol-version": "1999-01-01"}
    )
    assert stale.status_code == 400
    assert (
        stale.json()["error"]["code"] == -32022 and "2026-07-28" in stale.json()["error"]["data"]["supported"]
    )
    later = modern("tools/list")
    later["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2030-01-01"
    refused = client().post("/api/mcp", json=later, headers=headers("tools/list", version="2030-01-01"))
    assert refused.status_code == 400 and refused.json()["error"]["code"] == -32022


def test_a_request_under_the_new_version_header_carries_the_version_in_its_body() -> None:
    bare = client().post("/api/mcp", json=legacy("tools/list"), headers=headers("tools/list"))
    assert bare.status_code == 400 and bare.json()["error"]["code"] == -32602
    old = client().post("/api/mcp", json=legacy("tools/list"), headers={"mcp-protocol-version": "2025-11-25"})
    assert old.status_code == 200 and "resultType" not in old.json()["result"]
