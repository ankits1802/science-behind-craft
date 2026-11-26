import base64
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.data.skill_library import CRITIQUE_REFERENCE, reference_text
from app.models import User
from app.providers.router import Principal
from app.research.design_read import DRAWING_FAILED, READ, SKIPPED, DesignRead, ModelReading, NotRead
from app.research.design_read_prompt import DesignRequest
from app.research.page_render import DrawnProblem, RenderedImage, RenderResult
from app.research.page_report import page_report
from app.research.page_report_drawing import drawing_report, with_drawing
from app.research.page_report_rules import ReportInput
from app.services import page_design_read
from app.services.page_design_read import design_guidance, designed_preview
from app.services.page_reviews import DrawnPreview

from ..research.page_report_rules_fixtures import page_document

NOW = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
USER = User(id=uuid.UUID(int=7), name="Maker", email="maker@example.org", role="RESEARCHER", tokenVersion=0)
NOTES = {
    "notes": [
        {
            "chapter": "opening",
            "where": "the masthead",
            "problem": "A wall of text under the name, with no plate beside it.",
            "fix": "Set the dye plate beside the lede.",
        }
    ],
    "verdict": "The opening needs its plate.",
}


def shot(name: str, data: bytes) -> RenderedImage:
    encoded = base64.b64encode(data).decode("ascii")
    return RenderedImage(name=name, caption=f"{name} as drawn", width=390, height=844, data=encoded)


SHOTS = [shot("first-screen-390", b"\xff\xd8one"), shot("first-screen-1440", b"\xff\xd8two")]


def drawn(problems: list[DrawnProblem]) -> DrawnPreview:
    report = page_report(ReportInput(document=page_document()), {})
    outcome = RenderResult(problems=problems, images=SHOTS, seconds=3.0)
    return DrawnPreview(report=with_drawing(report, drawing_report(outcome)), images=SHOTS)


class Reader:
    def __init__(self, answer: ModelReading | NotRead) -> None:
        self.answer = answer
        self.asked: list[tuple[DesignRequest, Principal]] = []

    async def __call__(self, request: DesignRequest, principal: Principal) -> ModelReading | NotRead:
        self.asked.append((request, principal))
        return self.answer


class Session:
    async def commit(self) -> None:
        return None


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch) -> dict[str, DesignRead]:
    held: dict[str, DesignRead] = {}

    async def cached(_session: Any, key: str) -> DesignRead | None:
        found = held.get(key)
        return None if found is None else found.model_copy(update={"cached": True, "cost_usd": Decimal(0)})

    async def store(_session: Any, key: str, read: DesignRead, *, now: datetime) -> None:
        held[key] = read

    monkeypatch.setattr(page_design_read, "cached_read", cached)
    monkeypatch.setattr(page_design_read, "store_read", store)
    return held


def reading() -> ModelReading:
    return ModelReading(
        text=json.dumps(NOTES), provider="ANTHROPIC", model="claude-opus-5-5", cost_usd=Decimal("0.2")
    )


async def test_the_server_s_read_is_off_unless_the_preview_asks_for_it(cache: dict[str, DesignRead]) -> None:
    reader = Reader(reading())
    shown = await designed_preview(Session(), USER, drawn([]), asked=False, now=NOW, reader=reader)
    assert shown.report is not None and shown.report.design_read is None
    assert reader.asked == [] and cache == {}


async def test_a_failed_drawing_skips_the_read_without_calling_the_model(
    cache: dict[str, DesignRead],
) -> None:
    reader = Reader(reading())
    problem = DrawnProblem(width=390, label="page", problem="is 310px wider than the 390px screen")
    shown = await designed_preview(Session(), USER, drawn([problem]), asked=True, now=NOW, reader=reader)
    assert shown.report is not None and shown.report.design_read is not None
    assert (shown.report.design_read.state, shown.report.design_read.reason) == (SKIPPED, DRAWING_FAILED)
    assert reader.asked == [] and cache == {}


async def test_the_same_pictures_drawn_twice_are_read_once(cache: dict[str, DesignRead]) -> None:
    reader = Reader(reading())
    first = await designed_preview(Session(), USER, drawn([]), asked=True, now=NOW, reader=reader)
    again = await designed_preview(Session(), USER, drawn([]), asked=True, now=NOW, reader=reader)
    assert len(reader.asked) == 1 and len(cache) == 1
    assert first.report is not None and first.report.design_read is not None
    assert again.report is not None and again.report.design_read is not None
    made, held = first.report.design_read, again.report.design_read
    assert (made.state, made.cached, made.cost_usd, len(made.notes)) == (READ, False, Decimal("0.2"), 1)
    assert (held.cached, held.cost_usd, held.notes) == (True, Decimal(0), made.notes)
    request, principal = reader.asked[0]
    assert principal == Principal(user_id=USER.id, role="RESEARCHER")
    assert request.chapters == ("opening",) and request.pictures == 2


async def test_a_read_that_could_not_run_says_why_and_is_not_kept(cache: dict[str, DesignRead]) -> None:
    reader = Reader(NotRead(reason="The AI budget did not allow the designer's read."))
    shown = await designed_preview(Session(), USER, drawn([]), asked=True, now=NOW, reader=reader)
    assert shown.report is not None and shown.report.design_read is not None
    assert shown.report.design_read.state == SKIPPED and "budget" in (shown.report.design_read.reason or "")
    assert cache == {}


async def test_the_notes_never_change_a_verdict(cache: dict[str, DesignRead]) -> None:
    before = drawn([])
    shown = await designed_preview(Session(), USER, before, asked=True, now=NOW, reader=Reader(reading()))
    assert before.report is not None and shown.report is not None
    assert shown.report.design_read is not None and shown.report.design_read.notes
    assert (shown.report.passed, shown.report.failed, shown.report.judged) == (
        before.report.passed,
        before.report.failed,
        before.report.judged,
    )
    assert shown.report.rules == before.report.rules and shown.report.message == before.report.message


def test_the_server_s_read_asks_by_the_rubric_every_agent_reads() -> None:
    guidance = design_guidance()
    assert guidance.rubric == reference_text(CRITIQUE_REFERENCE)
    assert (
        guidance.sections.startswith("## 1. Principles")
        and "## 3. Colour tokens by role" in guidance.sections
    )
    assert "## 4. " not in guidance.sections and "(chemistry):" in guidance.rhythm
