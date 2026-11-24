import base64
from datetime import datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_page_tools
from app.models import PageDraft, User
from app.research.page_proposals import PageBundle, PagePreviewResult
from app.research.page_render import DrawnProblem, RenderedImage, RenderResult
from app.research.page_report import page_report
from app.research.page_report_drawing import drawing_report, with_drawing
from app.research.page_report_rules import ReportInput
from app.services.page_reviews import DrawnPreview

from ..research.page_report_rules_fixtures import page_document
from ..research.test_page_proposals import FACT
from .test_mcp_studio_tools import DRAFT_ID, NOW, SITE, FakeSession, call, context, draft_row, owned

SHOT = RenderedImage(
    name="first-screen-390",
    caption="The first screen at 390 px wide, as a reader opens the page",
    width=390,
    height=844,
    data=base64.b64encode(b"jpeg").decode("ascii"),
)
RENDERED = RenderResult(
    problems=[DrawnProblem(width=390, label="page", problem="is 310px wider than the 390px screen")],
    images=[SHOT],
    seconds=12.0,
)


async def previewed_draft(
    session: Any, user: User, bundle: PageBundle, *, site: str, now: datetime
) -> PagePreviewResult:
    assert len(bundle.facts) == 1
    return PagePreviewResult(
        subject=bundle.subject,
        page_url=f"{site}/crafts/Kutch-Ajrakh",
        preview_url=f"{site}/preview/token",
        expires_at=NOW + timedelta(hours=24),
        chapters=["opening", "chem"],
        components=1,
        sources=2,
        parts=[],
        message="Private to you for 24 hours.",
    )


async def drawn_with_a_problem(
    session: Any, user: User, previewed: Any, given: Any, **kwargs: Any
) -> DrawnPreview:
    return DrawnPreview(report=with_drawing(given, drawing_report(RENDERED)), images=[SHOT])


async def test_a_draft_s_preview_returns_the_private_link_the_report_and_its_pictures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = draft_row({"facts": [FACT]})
    report = page_report(ReportInput(document=page_document()), {})
    recorded: list[Any] = []

    async def reported(*args: Any, **kwargs: Any) -> Any:
        return report

    async def record(session: Any, draft: PageDraft, previewed: Any, kept: Any) -> None:
        recorded.append((draft.id, kept.failed))

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(row))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "record_preview", record)
    monkeypatch.setattr(mcp_page_tools.page_preview, "preview_page", previewed_draft)
    monkeypatch.setattr(mcp_page_tools.page_report, "preview_report", reported)
    monkeypatch.setattr(mcp_page_tools.page_reviews, "drawn_preview", drawn_with_a_problem)
    session = FakeSession()
    result = await call("preview_page", {"draft_id": str(DRAFT_ID)}, context(session=session))
    content = result["structuredContent"]
    assert content["previewUrl"] == f"{SITE}/preview/token" and content["draftId"] == str(DRAFT_ID)
    assert (content["report"]["failed"], len(content["report"]["rules"])) == (report.failed + 1, 28)
    assert content["report"]["drawing"]["state"] == "FAILED"
    assert recorded == [(DRAFT_ID, report.failed + 1)] and session.commits == 1
    assert result["content"][1:] == [
        {"type": "text", "text": SHOT.caption},
        {"type": "image", "data": SHOT.data, "mimeType": "image/jpeg"},
    ]
