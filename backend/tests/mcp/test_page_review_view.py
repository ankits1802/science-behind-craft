import base64
import hashlib
import re
import uuid
from typing import Any

from app.api.mcp_page_review import shown_pictures
from app.api.mcp_review_arguments import StagedChoice
from app.api.mcp_review_tools import staged_decision
from app.api.mcp_tools import TOOLS, ToolContext, answer
from app.models import DrawnPicture
from app.research.page_render import IMAGE_BYTES_MAX
from app.services.craft_resolver import CraftIndexStore

SITE = "https://kalavigyan.example"
CONTEXT = ToolContext(session=None, index=CraftIndexStore(), site=SITE)  # type: ignore[arg-type]
VIEW_URI = "ui://kalavigyan/page-review.html"
RAW_MARKUP = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function")
PROPOSAL = uuid.UUID("6f1c2a4e-8d3b-4c5a-9e7f-0a1b2c3d4e61")


async def result(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    reply = await answer({"jsonrpc": "2.0", "id": 3, "method": method, "params": params or {}}, CONTEXT)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def view() -> str:
    (content,) = (await result("resources/read", {"uri": VIEW_URI}))["contents"]
    return str(content["text"])


async def test_the_page_review_view_is_an_mcp_app_that_loads_nothing_and_review_queue_draws_with_it() -> None:
    listed = {resource["uri"]: resource for resource in (await result("resources/list"))["resources"]}
    resource = listed[VIEW_URI]
    assert resource["mimeType"] == "text/html;profile=mcp-app"
    assert resource["_meta"] == {
        "ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}}
    }
    assert TOOLS["review_queue"].meta()["ui/resourceUri"] == VIEW_URI
    assert "page" in TOOLS["review_queue"].arguments.model_fields


async def test_the_view_is_one_self_contained_page_that_draws_text_as_text() -> None:
    page = await view()
    assert "__KV_" not in page
    (script,) = re.findall(r"<script>(.*?)</script>", page, re.DOTALL)
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
    assert f"script-src 'sha256-{digest}'" in page
    assert "default-src 'none'" in page and "<script src" not in page and "<link" not in page
    assert [call for call in RAW_MARKUP if call in page] == []
    assert "textContent" in page and "structuredContent" in page and "ui/notifications/tool-result" in page


async def test_a_page_proposal_starts_as_one_line_marks_each_change_and_minimises_the_others() -> None:
    page = await view()
    assert "new BroadcastChannel(CHANNEL)" in page and '"kalavigyan-page-review"' in page
    assert "Show the changes" in page and "Minimise the changes" in page
    assert 'setAttribute("aria-expanded"' in page and 'setAttribute("aria-controls", "kv-full")' in page
    for word in (
        "Added",
        "Changed",
        "Removed",
        "As it stands",
        "As it will be",
        "a person confirms every one",
    ):
        assert word in page
    assert "ui/notifications/size-changed" in page and "setOpen(false)" in page


def picture(side: str, name: str, size: int) -> DrawnPicture:
    return DrawnPicture(
        proposalId=PROPOSAL,
        side=side,
        name=name,
        caption=f"{name} drawn",
        width=390,
        height=844,
        data=b"x" * size,
    )


def test_the_pictures_beside_a_page_proposal_put_each_first_screen_before_and_after_and_keep_to_the_budget() -> (
    None
):
    rows = [
        picture("AFTER", "chapter-history", 10),
        picture("AFTER", "first-screen-390", 10),
        picture("BEFORE", "first-screen-390", 10),
        picture("AFTER", "chapter-chem", IMAGE_BYTES_MAX),
        picture("BEFORE", "chapter-chem", 10),
    ]
    shown = shown_pictures(rows, ["chem"])
    assert [image.caption for image in shown] == [
        "As it stands: first-screen-390 drawn",
        "As it will be: first-screen-390 drawn",
        "As it stands: chapter-chem drawn",
    ]
    assert all(image.mime == "image/jpeg" for image in shown)


def test_an_admin_s_ai_stages_a_page_decision_with_its_scope_and_nothing_else_takes_one() -> None:
    choice = StagedChoice.model_validate(
        {
            "kind": "PAGES",
            "id": str(PROPOSAL),
            "action": "approve",
            "reason": "Every chemistry sentence is quoted.",
            "page": {"scope": "CHAPTER", "chapter": "chem"},
        }
    )
    staged = staged_decision(choice)
    assert staged.page is not None and (staged.page.scope, staged.page.chapter) == ("CHAPTER", "chem")
    for wrong in (
        {"kind": "PAGES", "page": None},
        {"kind": "FACTS", "page": {"scope": "PAGE"}},
        {"kind": "PAGES", "action": "raise", "page": {"scope": "PAGE"}},
    ):
        with_wrong = {**choice.model_dump(), **wrong}
        try:
            staged_decision(StagedChoice.model_validate(with_wrong))
        except ValueError:
            continue
        raise AssertionError(f"{wrong} was taken")
