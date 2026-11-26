import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.models import LayoutProposal, PagePreview, User
from app.research.design_critique import DesignCritique
from app.research.layout_proposals import LayoutReview, LayoutSubject
from app.research.page_proposals import PagePreviewResult, PageProposalResult, PageSubject, PartReport
from app.research.page_report import page_report
from app.research.page_report_rules import ReportInput
from app.services import page_critique
from app.services.page_critique import attach_critique, critiqued, layout_critique
from app.services.page_preview_links import preview_key, signed_token
from app.services.page_reviews import DrawnPreview

from ..research.page_report_rules_fixtures import page_document

NOW = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
SITE = "https://kalavigyan.example"
USER = User(id=uuid.UUID(int=11), name="Maker", email="maker@example.org", role="RESEARCHER", tokenVersion=0)
PREVIEW_ID = uuid.UUID(int=21)
LAYOUT_ID = uuid.UUID(int=31)
SUBJECT = PageSubject(kind="craft", slug="Sanganeri-Hand-Block-Printing")
CRITIQUE = DesignCritique.model_validate(
    {
        "verdict": "The making chapter is a wall of prose.",
        "notes": [
            {
                "chapter": "made",
                "where": "the eight paragraphs on washing",
                "problem": "A wall of text with no figure beside it.",
                "fix": "Step through the washes with a stage player beside the first paragraph.",
            }
        ],
    }
)


class Session:
    def __init__(self, rows: dict[Any, Any] | None = None) -> None:
        self.rows = rows or {}
        self.flushed = 0

    async def get(self, model: Any, key: Any) -> Any:
        return self.rows.get((model, key))

    async def flush(self) -> None:
        self.flushed += 1


class Untouched:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the session was used ({name})")


def previewed() -> PagePreviewResult:
    token = signed_token(PREVIEW_ID, USER.id, NOW + timedelta(hours=24), preview_key())
    return PagePreviewResult(
        subject=SUBJECT,
        page_url=f"{SITE}/crafts/{SUBJECT.slug}",
        preview_url=f"{SITE}/preview/{token}",
        expires_at=NOW + timedelta(hours=24),
        chapters=["opening", "made"],
        components=1,
        sources=2,
        parts=[],
        message="Private to you for 24 hours.",
    )


def drawn() -> DrawnPreview:
    return DrawnPreview(report=page_report(ReportInput(document=page_document()), {}))


def proposed(*parts: PartReport) -> PageProposalResult:
    return PageProposalResult(
        subject=SUBJECT,
        page_url=f"{SITE}/crafts/{SUBJECT.slug}",
        accepted=1,
        refused=0,
        parts=list(parts),
        message=".",
    )


async def test_a_preview_without_a_critique_is_left_as_it_is() -> None:
    before = drawn()
    after = await critiqued(Untouched(), USER, previewed(), before, critique=None, now=NOW)  # type: ignore[arg-type]
    assert after is before and before.report is not None and before.report.critique is None


async def test_a_critique_is_kept_on_its_preview_and_shown_in_the_report_without_changing_a_verdict() -> None:
    row = PagePreview(id=PREVIEW_ID, userId=USER.id)
    session = Session({(PagePreview, PREVIEW_ID): row})
    before = drawn()
    after = await critiqued(session, USER, previewed(), before, critique=CRITIQUE, now=NOW)  # type: ignore[arg-type]
    assert row.critique == CRITIQUE.model_dump(mode="json") and session.flushed == 1
    assert after.report is not None and before.report is not None
    assert after.report.critique == CRITIQUE
    assert (after.report.passed, after.report.failed, after.report.judged, after.report.rules) == (
        before.report.passed,
        before.report.failed,
        before.report.judged,
        before.report.rules,
    )


async def test_a_proposal_without_an_accepted_layout_carries_no_critique_and_reads_nothing() -> None:
    refused = PartReport(part="layout", index=0, outcome="REFUSED", message="stale")
    component = PartReport(part="component", index=0, outcome="ACCEPTED", id=str(uuid.uuid4()), message="ok")
    for result in (proposed(), proposed(refused), proposed(component)):
        await attach_critique(Untouched(), USER, result, now=NOW)  # type: ignore[arg-type]


async def test_the_latest_critique_goes_to_the_reviewer_with_the_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[tuple[uuid.UUID, tuple[str, str]]] = []

    async def latest(_session: Any, user_id: uuid.UUID, subject: tuple[str, str], *, now: datetime) -> Any:
        asked.append((user_id, subject))
        return CRITIQUE

    monkeypatch.setattr(page_critique, "latest_critique", latest)
    proposal = LayoutProposal(id=LAYOUT_ID)
    session = Session({(LayoutProposal, LAYOUT_ID): proposal})
    layout = PartReport(
        part="layout", index=0, outcome="ACCEPTED", status="PENDING", id=str(LAYOUT_ID), message="ok"
    )
    await attach_critique(session, USER, proposed(layout), now=NOW)  # type: ignore[arg-type]
    assert asked == [(USER.id, ("craft", SUBJECT.slug))]
    assert layout_critique(proposal) == CRITIQUE and session.flushed == 1


def test_a_stored_critique_is_read_back_and_a_missing_or_broken_one_is_none() -> None:
    assert layout_critique(LayoutProposal(critique=CRITIQUE.model_dump(mode="json"))) == CRITIQUE
    assert layout_critique(LayoutProposal(critique=None)) is None
    assert layout_critique(LayoutProposal(critique={"notes": []})) is None


def test_the_layout_review_carries_the_critique_and_is_whole_without_one() -> None:
    fields = {
        "subject": LayoutSubject(kind="craft", slug=SUBJECT.slug),
        "subject_name": "Sanganeri Hand Block Printing",
        "page_url": "/crafts/Sanganeri-Hand-Block-Printing",
        "base_version": 0,
        "current_version": 0,
        "stale": False,
        "note": None,
        "entry_count": 0,
        "changes": [],
    }
    shown = LayoutReview(**fields, critique=CRITIQUE).model_dump(mode="json")
    assert shown["critique"]["notes"][0]["where"] == "the eight paragraphs on washing"
    assert LayoutReview(**fields).model_dump(mode="json")["critique"] is None
