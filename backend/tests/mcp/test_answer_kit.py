import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.api.mcp_tools import ToolContext, answer
from app.services.craft_resolver import CraftIndexStore

BACKEND = Path(__file__).resolve().parents[2]
DESIGN = BACKEND / "app" / "data" / "design"
TOKENS = json.loads((DESIGN / "tokens.json").read_bytes().decode("utf-8"))
SITE = "https://kalavigyan.example"
CONTEXT = ToolContext(session=None, index=CraftIndexStore(), site=SITE)  # type: ignore[arg-type]
KIT_URI = "kalavigyan://design/answer-kit.md"
VIEW_URI = "ui://kalavigyan/answer.html"
RAW_MARKUP = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function")


async def result(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    reply = await answer({"jsonrpc": "2.0", "id": 3, "method": method, "params": params or {}}, CONTEXT)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def read(uri: str) -> dict[str, Any]:
    (content,) = (await result("resources/read", {"uri": uri}))["contents"]
    return content


async def test_the_answer_kit_and_the_answer_view_are_listed_beside_the_tokens() -> None:
    listed = {resource["uri"]: resource for resource in (await result("resources/list"))["resources"]}
    assert {KIT_URI, VIEW_URI, "kalavigyan://design/tokens.json"} <= set(listed)
    assert listed[KIT_URI]["mimeType"] == "text/markdown"
    assert listed[VIEW_URI]["mimeType"] == "text/html;profile=mcp-app"
    no_network = {"connectDomains": [], "resourceDomains": []}
    assert listed[VIEW_URI]["_meta"] == {"ui": {"prefersBorder": True, "csp": no_network}}
    assert "_meta" not in listed[KIT_URI]


async def test_the_kit_spells_out_the_answer_s_parts_with_the_light_and_dark_tokens() -> None:
    kit = await read(KIT_URI)
    text = kit["text"]
    assert kit["mimeType"] == "text/markdown" and "{{tokens}}" not in text
    for heading in ("## The order", "## Sentences and citation clusters", "## Component cards", "## Sources"):
        assert heading in text
    indigo = TOKENS["color"]["indigo"]
    assert f"| `--indigo` | {indigo['role']} | {indigo['light']['hex']} | {indigo['dark']['hex']} |" in text
    assert "Centre of Excellence" in text and "answerUrl" in text


async def test_the_view_is_one_self_contained_page_whose_one_script_its_policy_names() -> None:
    view = await read(VIEW_URI)
    page = view["text"]
    assert view["mimeType"] == "text/html;profile=mcp-app" and "_meta" in view
    assert "__KV_" not in page
    (script,) = re.findall(r"<script>(.*?)</script>", page, re.DOTALL)
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
    assert f"script-src 'sha256-{digest}'" in page
    assert "default-src 'none'" in page and "<script src" not in page and "<link" not in page
    assert re.findall(r"""(?:src|href)=["']https?:""", page) == []


async def test_the_view_draws_every_text_as_text_and_links_only_https() -> None:
    page = (await read(VIEW_URI))["text"]
    assert [call for call in RAW_MARKUP if call in page] == []
    assert "textContent" in page and 'url.protocol === "https:"' in page
    assert "structuredContent" in page and "ui/notifications/tool-result" in page


async def test_the_view_carries_the_light_and_dark_tokens() -> None:
    page = (await read(VIEW_URI))["text"]
    ground = TOKENS["color"]["ground"]
    assert f"--ground:{ground['light']['hex']};" in page
    assert f':root[data-theme="dark"]{{color-scheme:dark;--ground:{ground["dark"]["hex"]};' in page
    assert TOKENS["type"]["families"]["reading"]["stack"] in page
