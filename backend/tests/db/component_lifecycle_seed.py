import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    ClaimSource,
    ComponentProposal,
    Concept,
    CraftSteward,
    KnowledgePiece,
    KnowledgePieceSubject,
    User,
)
from app.research.component_specs_general_delivery import DELIVERED_KEY

from ..research.general_spec_fixtures import TABLE, table_units
from .page_documents_seed import ADMIN, ALUM, BARE, CRAFT, CRAFT_CLAIM, CRAFT_SLUG, PAPER, seed

__all__ = [
    "ADMIN",
    "BARE_CLAIM",
    "FOREIGN",
    "NEW",
    "NOW",
    "OWN",
    "OWN_PROPOSAL",
    "PROPOSER",
    "SITE",
    "STEWARD",
    "STRANGER",
    "lifecycle_seed",
    "person",
    "replacement",
]

NOW = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
SITE = "https://kalavigyan.example"
PROPOSER = uuid.UUID("9e1f0000-0000-4000-8000-000000000001")
STRANGER = uuid.UUID("9e1f0000-0000-4000-8000-000000000002")
STEWARD = uuid.UUID("9e1f0000-0000-4000-8000-000000000003")
OWN_PROPOSAL = uuid.UUID("9e1f0000-0000-4000-8000-000000000010")
BARE_CONCEPT = uuid.UUID("9e1f0000-0000-4000-8000-000000000020")
BARE_CLAIM = uuid.UUID("9e1f0000-0000-4000-8000-000000000021")
OWN = "page-docs-test-craft/chemistry/alum-plain-table"
NEW = "page-docs-test-craft/chemistry/alum-dated-record"
FOREIGN = "shared/chemistry/page-docs-bare-alum"


async def lifecycle_seed(session: AsyncSession) -> None:
    await seed(session)
    session.add_all(
        User(id=user_id, name=name, email=f"{user_id.hex}@example.org", role="RESEARCHER")
        for user_id, name in ((PROPOSER, "Proposer"), (STRANGER, "Stranger"), (STEWARD, "Steward"))
    )
    await session.flush()
    session.add(CraftSteward(userId=STEWARD, craftId=CRAFT, adoptedAt=NOW))
    session.add(_own_proposal())
    session.add(Concept(id=BARE_CONCEPT, craftId=BARE, type="MATERIAL", name="Bare alum"))
    await session.flush()
    session.add(_bare_claim())
    await session.flush()
    session.add(
        ClaimSource(claimId=BARE_CLAIM, sourceId=PAPER, quote="bare alum", locator="p. 9", quoteCheck="PASS")
    )
    own = _piece(OWN, CRAFT, CRAFT_CLAIM, "Plain alum table", proposal=OWN_PROPOSAL)
    foreign = _piece(FOREIGN, None, BARE_CLAIM, "Bare craft alum record")
    session.add_all([own, foreign])
    await session.flush()
    session.add_all(
        [
            KnowledgePieceSubject(pieceId=own.id, kind="CRAFT", craftId=CRAFT),
            KnowledgePieceSubject(pieceId=foreign.id, kind="CONCEPT", conceptId=ALUM),
        ]
    )
    await session.flush()


async def person(session: AsyncSession, user_id: uuid.UUID) -> User:
    found = await session.scalar(select(User).where(User.id == user_id))
    assert found is not None
    return found


def replacement(**changes: Any) -> dict[str, Any]:
    return {
        "label": NEW,
        "title": "Mordant record of alum on cotton",
        "description": "The mordant record of what alum does on the cotton, dated where the record dates it.",
        "kind": "fact_table",
        "field": "CHEMISTRY",
        "craftSlug": CRAFT_SLUG,
        "subjects": [{"kind": "CRAFT", "key": CRAFT_SLUG}],
        "replaces": OWN,
        "spec": TABLE,
        "units": table_units(CRAFT_CLAIM),
    } | changes


def _own_proposal() -> ComponentProposal:
    return ComponentProposal(
        id=OWN_PROPOSAL,
        proposerId=PROPOSER,
        label=OWN,
        title="Plain alum table",
        description="A plain table of the alum mordant, proposed and registered before this test.",
        kind="fact_table",
        field="CHEMISTRY",
        craftId=CRAFT,
        subjects=[{"kind": "CRAFT", "key": CRAFT_SLUG}],
        status="APPROVED",
        reviewedById=ADMIN,
        reviewedAt=NOW,
        spec=TABLE,
        units=table_units(CRAFT_CLAIM),
        claimIds=[CRAFT_CLAIM],
    )


def _bare_claim() -> Claim:
    return Claim(
        id=BARE_CLAIM,
        subjectType="CONCEPT",
        subjectId=BARE_CONCEPT,
        predicate="states",
        text="The bare craft's printers mordant with alum from its own pits.",
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        field="CHEMISTRY",
    )


def _piece(
    label: str,
    craft_id: uuid.UUID | None,
    claim_id: uuid.UUID,
    title: str,
    *,
    proposal: uuid.UUID | None = None,
) -> KnowledgePiece:
    payload: dict[str, Any] = {DELIVERED_KEY: {"spec": TABLE, "units": table_units(claim_id)}}
    if proposal is not None:
        payload["proposalId"] = str(proposal)
    return KnowledgePiece(
        craftId=craft_id,
        kind="fact_table",
        facet="CHEMISTRY",
        topicKey=f"component:{label}",
        language="en",
        depth="EXPERT",
        payload=payload,
        claimIds=[claim_id],
        sourceIds=[str(PAPER)],
        contentHash=uuid.uuid4().hex + uuid.uuid4().hex,
        label=label,
        title=title,
        description=f"{title}, a component registered before this test.",
    )
