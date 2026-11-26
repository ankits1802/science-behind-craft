import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_review_tools, mcp_staged_confirm
from app.api.mcp_tools import ToolContext
from app.models import StagedReview, StagedReviewItem, User
from app.research.page_proposal_review import PageScope
from app.research.staged_review_words import PageTouches, proposal_review_link
from app.research.staged_reviews import StagedBatchView, StagedDecision, StagedItemView, stored_decision
from app.services import staged_review_summary
from app.services.craft_resolver import CraftIndexStore
from app.services.oauth_bearer import McpCaller
from app.services.staged_review_confirm import Confirmed
from app.services.staged_reviews import Staged

from .modern_client import FORMS, modern, tool_call

__all__ = [
    "ADMIN_ID",
    "BATCH_ID",
    "GRANT_ID",
    "LABELS",
    "NOTE",
    "OTHER_ID",
    "PROPOSAL",
    "REVIEW",
    "SITE",
    "STAGE",
    "Desk",
    "context",
    "person",
    "staging",
]

SITE = "https://kalavigyan.example"
REVIEW = f"{SITE}/admin/review"
ADMIN_ID = uuid.UUID("0e000000-0000-4000-8000-0000000243a1")
OTHER_ID = uuid.UUID("0e000000-0000-4000-8000-0000000243a2")
GRANT_ID = uuid.UUID("0e000000-0000-4000-8000-0000000243b1")
TOKEN_ID = uuid.UUID("0e000000-0000-4000-8000-0000000243b2")
BATCH_ID = uuid.UUID("0e000000-0000-4000-8000-0000000243c1")
PROPOSAL = uuid.UUID("0e000000-0000-4000-8000-0000000243d1")
FACTS = (uuid.UUID("0e000000-0000-4000-8000-0000000243e1"), uuid.UUID("0e000000-0000-4000-8000-0000000243e2"))
ITEMS = tuple(uuid.UUID(f"0e000000-0000-4000-8000-0000000243f{n}") for n in range(3))
WHY = "Both quotes say this of the vat, word for word."
NOTE = "Refreshing the 1 pages these decisions touched now."
DECISIONS = [
    {"kind": "FACTS", "id": str(FACTS[0]), "action": "approve", "reason": WHY},
    {"kind": "FACTS", "id": str(FACTS[1]), "action": "reject", "reason": WHY},
    {
        "kind": "PAGES",
        "id": str(PROPOSAL),
        "action": "approve",
        "reason": WHY,
        "page": {"scope": "CHAPTER", "chapter": "chem"},
    },
]
LABELS = (
    "An indigo vat turns blue at its surface.",
    "Lime keeps the indigo vat alkaline.",
    "Page proposal for Sanganeri Hand Block Printing: the chapter chem",
)
STAGE = {"decisions": DECISIONS}


class Desk:
    def __init__(self) -> None:
        self.batch: StagedReview | None = None
        self.items: list[StagedReviewItem] = []
        self.proposer: uuid.UUID | None = None
        self.status = "OPEN"
        self.staged = 0
        self.confirmed: list[frozenset[int]] = []
        self.finished = 0
        self.commits = 0
        self.rollbacks = 0

    def patch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mcp_review_tools, "stage_decisions", self.stage)
        monkeypatch.setattr(staged_review_summary, "batch_items", self.batch_items)
        monkeypatch.setattr(staged_review_summary, "page_touches", self.touches)
        monkeypatch.setattr(mcp_staged_confirm, "confirm_as_staged", self.confirm)
        monkeypatch.setattr(mcp_staged_confirm, "finish_confirmed", self.finish)
        monkeypatch.setattr(mcp_staged_confirm, "batch_view", self.view)

    async def get(self, model: Any, key: uuid.UUID, **_: Any) -> Any:
        return self.batch if self.batch is not None and key == self.batch.id else None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def stage(
        self, session: Any, asked: Sequence[StagedDecision], caller: McpCaller, *, now: datetime
    ) -> Staged:
        self.staged += 1
        self.batch = StagedReview(
            id=BATCH_ID,
            proposerId=self.proposer or caller.user.id,
            grantId=caller.grant_id,
            clientName=caller.client_name,
            status=self.status,
            createdAt=now,
            expiresAt=now + timedelta(days=3),
        )
        self.items = [_item(place, decision) for place, decision in enumerate(asked)]
        return Staged(batch=self.batch, items=list(self.items), today=len(asked))

    async def batch_items(self, session: Any, batch_id: uuid.UUID) -> list[StagedReviewItem]:
        return list(self.items) if batch_id == BATCH_ID else []

    async def touches(
        self, session: Any, proposal_id: uuid.UUID, scope: PageScope, *, site: str
    ) -> PageTouches:
        link = proposal_review_link(site, proposal_id)
        return PageTouches(("The chemistry",), ("Black and red from one dye bath",), link)

    async def confirm(
        self, session: Any, batch_id: uuid.UUID, positions: frozenset[int], confirmer: User, *, now: datetime
    ) -> Confirmed:
        assert self.batch is not None and batch_id == self.batch.id and confirmer.id == ADMIN_ID
        self.confirmed.append(frozenset(positions))
        for item in self.items:
            item.state = "APPLIED" if item.position in positions else "SKIPPED"
        self.batch.status = "CONFIRMED"
        return Confirmed(self.batch)

    async def finish(
        self, session: Any, confirmed: Confirmed, confirmer: User, background: Any, *, now: datetime
    ) -> str:
        self.finished += 1
        return NOTE

    async def view(
        self, session: Any, batch: StagedReview, *, now: datetime, refresh: str | None = None
    ) -> StagedBatchView:
        return StagedBatchView(
            id=batch.id,
            status=batch.status,
            client_name=batch.clientName,
            proposed_by="Admin Reviewer",
            created_at=batch.createdAt,
            expires_at=batch.expiresAt,
            refresh=refresh,
            items=[_view(item) for item in self.items],
        )


class Shelf:
    def start(self, work: Any, *, name: str) -> None:
        work.close()


def person(user_id: uuid.UUID = ADMIN_ID, role: str = "ADMIN") -> User:
    email = f"{user_id.hex[:8]}@example.org"
    return User(id=user_id, name="Admin Reviewer", email=email, role=role, tokenVersion=0)


def context(
    desk: Desk,
    *,
    scopes: Sequence[str] = ("read", "review"),
    user: User | None = None,
    grant: uuid.UUID = GRANT_ID,
) -> ToolContext:
    who = user or person()
    caller = McpCaller(who, frozenset(scopes), grant, TOKEN_ID, "Claude")
    return ToolContext(
        session=desk,  # type: ignore[arg-type]
        index=CraftIndexStore(),
        site=SITE,
        user=who,
        scopes=frozenset(scopes),
        caller=caller,
        background=Shelf(),
    )


def staging(
    arguments: dict[str, Any] = STAGE, *, capabilities: dict[str, Any] = FORMS, **extra: Any
) -> dict[str, Any]:
    return modern("tools/call", tool_call("stage_reviews", arguments, **extra), capabilities=capabilities)


def _item(place: int, decision: StagedDecision) -> StagedReviewItem:
    return StagedReviewItem(
        id=ITEMS[place],
        batchId=BATCH_ID,
        position=place,
        kind=decision.kind,
        itemId=decision.id,
        action=decision.action,
        decision=stored_decision(decision),
        label=LABELS[place],
        state="STAGED",
    )


def _view(item: StagedReviewItem) -> StagedItemView:
    return StagedItemView(
        id=item.id,
        position=item.position,
        label=item.label,
        decision=StagedDecision.model_validate(item.decision),
        state=item.state,
    )
