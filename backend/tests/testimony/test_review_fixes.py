import json
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from app.api.testimony_deps import OWN_DETAIL, refusal
from app.models import ArtisanContribution, ArtisanConversation, ArtisanProfile, Craft, User
from app.research.testimony import NAME_HELD_BACK
from app.services import testimony_claims, testimony_screens, testimony_withdrawal, testimony_writes
from app.services.testimony_store import (
    ContributionProblems,
    OwnContribution,
    _approved_rows,
    _filters,
    refuse_own,
)
from app.services.testimony_views import review_item

ARTISAN = uuid.UUID("2b3c4d5e-6f70-4a81-92a3-b4c5d6e7f809")
REVIEWER = uuid.UUID("0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d")
CRAFT = uuid.UUID("8e9f0a1b-2c3d-4e5f-8a6b-7c8d9e0f1a2b")
CONVERSATION = uuid.UUID("9b2c4d6e-8f0a-4b1c-9d2e-3f4a5b6c7d8e")
CONTRIBUTION = uuid.UUID("3f1e8b7a-2c4d-4e5f-9a1b-0c2d3e4f5a6b")
CLAIM = uuid.UUID("1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d")
NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
NAMED_QUOTE = "रमेश कहते हैं कि हम कपड़े को बहते पानी में धोते हैं"
CLEAN_QUOTE = "फिटकरी के बाद हम कपड़े को बहते पानी में धोते हैं"


def contribution(**changes: Any) -> ArtisanContribution:
    fields: dict[str, Any] = {
        "id": CONTRIBUTION,
        "conversationId": CONVERSATION,
        "userId": ARTISAN,
        "craftId": CRAFT,
        "turnId": uuid.uuid4(),
        "ordinal": 3,
        "status": "PENDING",
        "quote": CLEAN_QUOTE,
        "quoteLanguage": "hi",
        "english": "After the alum we wash the cloth in running water",
        "englishSource": "MACHINE",
        "claimText": "After the alum bath the cloth is washed in running water.",
        "discipline": "PROCESS",
        "conceptType": "PROCESS_STAGE",
        "conceptName": "Washing in running water",
        "startMs": 65_000,
        "endMs": 72_000,
        "locatorPrecision": "WORD",
        "screens": [],
        "corroboratingClaimIds": [],
        "version": 2,
        "createdAt": NOW,
    }
    return ArtisanContribution(**(fields | changes))


def artisan_rows(credit_mode: str = "CRAFT_AND_DISTRICT") -> dict[tuple[type, Any], Any]:
    return {
        (User, ARTISAN): User(id=ARTISAN, email="artisan@example.org", name="रमेश कुमार", role="ARTISAN"),
        (ArtisanProfile, ARTISAN): ArtisanProfile(
            userId=ARTISAN,
            districtLgd=468,
            spokenLanguage="hi",
            creditMode=credit_mode,
            creditName="रमेश कुमार" if credit_mode == "FULL_NAME" else None,
            creditShortName=None,
        ),
    }


class Session:
    def __init__(self, rows: dict[tuple[type, Any], Any] | None = None, listed: Iterable[Any] = ()) -> None:
        self.rows = dict(rows or {})
        self.listed = list(listed)
        self.events: list[tuple[Any, ...]] = []
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.watched: ArtisanContribution | None = None

    async def get(self, model: type, key: Any, **_options: Any) -> Any:
        return self.rows.get((model, key))

    async def scalar(self, _statement: Any) -> Any:
        return None

    async def scalars(self, statement: Any) -> list[Any]:
        self.statements.append(statement)
        return list(self.listed)

    async def execute(self, statement: Any) -> None:
        self.events.append(("execute", statement.table.name))

    async def flush(self) -> None:
        watched = self.watched
        self.events.append(("flush", watched.status, watched.claimId) if watched else ("flush",))

    def add(self, row: Any) -> None:
        self.added.append(row)


def sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


async def test_withdrawing_an_approved_item_clears_its_claim_before_the_claim_is_erased() -> None:
    item = contribution(status="APPROVED", claimId=CLAIM, approvedAt=NOW)
    session = Session()
    session.watched = item
    await testimony_withdrawal._taken_back(session, item, NOW)
    assert session.events[0] == ("flush", "WITHDRAWN", None)
    deleted = [event[1] for event in session.events[1:]]
    assert deleted == ["ClaimSource", "Claim"]
    assert (item.quote, item.english, item.claimText, item.textsClearedAt) == (None, None, None, NOW)
    assert (item.withdrawnAt, item.version) == (NOW, 3)


async def test_clearing_a_rejected_item_also_drops_its_claim_after_the_row_lets_go() -> None:
    item = contribution(status="REJECTED", claimId=CLAIM, rejectReason="UNCLEAR", rejectedAt=NOW)
    session = Session()
    session.watched = item
    await testimony_withdrawal._claim_dropped(session, item, NOW)
    assert session.events[0] == ("flush", "REJECTED", None)
    assert session.events[-1] == ("execute", "Claim")


def test_a_reviewer_never_reviews_their_own_words() -> None:
    with pytest.raises(OwnContribution):
        refuse_own(contribution(), SimpleNamespace(id=ARTISAN))
    refuse_own(contribution(), SimpleNamespace(id=REVIEWER))
    answer = refusal(OwnContribution("own"))
    assert answer.status_code == 403
    assert json.loads(answer.body) == {"detail": OWN_DETAIL}


async def test_approve_edit_and_reject_refuse_the_reviewers_own_item() -> None:
    item = contribution()
    own = SimpleNamespace(id=ARTISAN)
    session = Session({(ArtisanContribution, CONTRIBUTION): item, **artisan_rows()})
    with pytest.raises(OwnContribution):
        await testimony_writes.approve(
            session, CONTRIBUTION, own, version=2, english_checked=False, corroborating_ids=[], now=NOW
        )
    with pytest.raises(OwnContribution):
        await testimony_writes.edit(
            session,
            CONTRIBUTION,
            own,
            change=testimony_writes.ContributionEdit(version=2, claim_text="Washed in running water."),
            turn_text=CLEAN_QUOTE,
            now=NOW,
        )
    with pytest.raises(OwnContribution):
        await testimony_writes.reject(
            session, CONTRIBUTION, own, version=2, reason="UNCLEAR", note=None, now=NOW
        )
    assert item.status == "PENDING" and item.version == 2


async def test_approve_screens_against_the_current_credit_not_the_stored_screens() -> None:
    item = contribution(quote=NAMED_QUOTE, screens=[])
    session = Session({(ArtisanContribution, CONTRIBUTION): item, **artisan_rows()})
    with pytest.raises(ContributionProblems) as refused:
        await testimony_writes.approve(
            session,
            CONTRIBUTION,
            SimpleNamespace(id=REVIEWER),
            version=2,
            english_checked=False,
            corroborating_ids=[],
            now=NOW,
        )
    assert "held-back name" in str(refused.value)
    assert item.screens == [NAME_HELD_BACK]
    assert item.status == "PENDING"


async def test_a_credit_change_rescreens_waiting_and_shown_items() -> None:
    shown = contribution(id=uuid.uuid4(), status="APPROVED", quote=NAMED_QUOTE, claimId=CLAIM, approvedAt=NOW)
    waiting = contribution(id=uuid.uuid4())
    session = Session(artisan_rows(), listed=[shown, waiting])
    assert await testimony_screens.rescreen_contributions(session, ARTISAN) == 1
    assert (shown.screens, shown.version) == ([NAME_HELD_BACK], 3)
    assert (waiting.screens, waiting.version) == ([], 2)
    named = Session(artisan_rows("FULL_NAME"), listed=[shown])
    assert await testimony_screens.rescreen_contributions(named, ARTISAN) == 0
    assert (shown.screens, shown.version) == ([], 4)


def test_a_screened_approved_item_is_never_read_as_shown_testimony() -> None:
    assert "cardinality(" in sql(_approved_rows())


def test_the_review_queue_leaves_out_the_reviewers_own_items() -> None:
    (condition,) = _filters(craft_id=None, language=None, reviewer_id=REVIEWER)
    assert sql(condition).startswith('"ArtisanContribution"."userId" !=')
    assert _filters(craft_id=None, language=None) == []


async def test_testimony_attaches_only_to_testimony_concepts() -> None:
    session = Session()
    concept = await testimony_claims.testimony_concept(session, CRAFT, "PROCESS_STAGE", "Washing  in water")
    (statement,) = session.statements
    text = sql(statement)
    assert "\"originRef\" = 'artisan-testimony'" in text
    assert "'ATTRIBUTE_REQUIRED'" in text and "'OPEN'" not in text
    assert (concept.sensitivity, concept.originRef, concept.name) == (
        "ATTRIBUTE_REQUIRED",
        "artisan-testimony",
        "Washing in water",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "WITHDRAWN", "withdrawnAt": NOW, "quote": None, "english": None, "claimText": None},
        {
            "status": "REJECTED",
            "rejectReason": "UNCLEAR",
            "rejectedAt": NOW,
            "textsClearedAt": NOW,
            "quote": None,
            "english": None,
            "claimText": None,
        },
    ],
)
async def test_a_closed_item_shows_reviewers_no_words_or_context(changes: dict[str, Any]) -> None:
    item = contribution(**changes)
    session = Session(
        {
            (Craft, CRAFT): Craft(id=CRAFT, slug="kutch-ajrakh", name="Ajrakh Printing"),
            (ArtisanConversation, CONVERSATION): ArtisanConversation(
                id=CONVERSATION, userId=ARTISAN, craftId=CRAFT, startedAt=NOW
            ),
        }
    )
    turns = {str(item.turnId): {"id": str(item.turnId), "ordinal": 3, "text": CLEAN_QUOTE}}
    body = await review_item(session, item, turns=turns, links=None, now=NOW)
    assert set(body) == {"id", "status", "craft", "withdrawnAt"}
    assert CLEAN_QUOTE not in json.dumps(body, ensure_ascii=False)
