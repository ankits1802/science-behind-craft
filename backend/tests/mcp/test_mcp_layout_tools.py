import json
import uuid
from typing import Any

import pytest

from app.api import mcp_layout_tools
from app.api.mcp_tools import ToolContext, answer
from app.core.errors import InvalidInput
from app.research.page_layout import PageLayout
from app.services.craft_resolver import CraftIndexStore
from app.services.open_work_subjects import WorkSubject

CONTEXT = ToolContext(session=None, index=CraftIndexStore(), site="https://kalavigyan.example")  # type: ignore[arg-type]
TEXTILES = WorkSubject(uuid.UUID(int=3), "category", "Textile-Craft-Category", "Textiles", gi=False)
BAGH = WorkSubject(uuid.UUID(int=4), "craft", "Bagh-Print", "Bagh Print", gi=True)
STORED = PageLayout.model_validate(
    {
        "subjectKind": "craft",
        "subjectSlug": "Bagh-Print",
        "version": 2,
        "entries": [{"ref": "bagh-print/pictures/i02", "chapter": "glance", "order": 1, "role": "HERO"}],
    }
)


def request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 7, "method": method, "params": params}


@pytest.fixture(autouse=True)
def stored(monkeypatch: pytest.MonkeyPatch) -> None:
    async def subject(session: Any, kind: str, slug: str) -> WorkSubject:
        found = {(s.kind, s.slug): s for s in (TEXTILES, BAGH)}.get((kind, slug))
        if found is None:
            raise InvalidInput(
                f"No {kind} has the slug {slug}; find_crafts gives the slugs of crafts and families."
            )
        return found

    async def layout(session: Any, subject: WorkSubject) -> PageLayout | None:
        return STORED if subject is BAGH else None

    monkeypatch.setattr(mcp_layout_tools, "subject_by_key", subject)
    monkeypatch.setattr(mcp_layout_tools, "layout_of", layout)


async def call(arguments: dict[str, Any]) -> dict[str, Any]:
    reply = await answer(request("tools/call", {"name": "get_layout", "arguments": arguments}), CONTEXT)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def test_get_layout_is_listed_as_a_read_only_tool_for_any_connection() -> None:
    reply = await answer(request("tools/list", {}), CONTEXT)
    assert reply is not None
    (tool,) = [tool for tool in reply["result"]["tools"] if tool["name"] == "get_layout"]
    assert tool["annotations"]["readOnlyHint"] is True
    assert tool["inputSchema"]["required"] == ["subject_kind", "slug"]
    assert tool["inputSchema"]["properties"]["subject_kind"]["enum"] == ["craft", "family", "category"]
    assert "never holds a fact" in tool["description"]


async def test_get_layout_returns_the_stored_record_and_the_page() -> None:
    result = await call({"subject_kind": "craft", "slug": "Bagh-Print"})
    assert result["isError"] is False
    structured = result["structuredContent"]
    assert structured["layout"]["version"] == 2
    assert structured["layout"]["entries"][0] == {
        "ref": "bagh-print/pictures/i02",
        "chapter": "glance",
        "order": 1,
        "role": "HERO",
        "crop": None,
        "size": None,
        "caption": None,
    }
    assert structured["pageUrl"] == "https://kalavigyan.example/crafts/Bagh-Print"
    assert json.loads(result["content"][0]["text"]) == structured


async def test_a_page_without_a_layout_answers_null_and_a_category_its_category_page() -> None:
    structured = (await call({"subject_kind": "category", "slug": "Textile-Craft-Category"}))[
        "structuredContent"
    ]
    assert structured["layout"] is None
    assert structured["pageUrl"] == "https://kalavigyan.example/categories/Textile-Craft-Category"


async def test_an_unknown_slug_or_kind_is_a_tool_error_the_model_can_correct() -> None:
    unknown = await call({"subject_kind": "family", "slug": "No-Such-Family"})
    assert unknown["isError"] is True
    assert "find_crafts" in unknown["content"][0]["text"]
    wrong = await call({"subject_kind": "planet", "slug": "Bagh-Print"})
    assert wrong["isError"] is True
