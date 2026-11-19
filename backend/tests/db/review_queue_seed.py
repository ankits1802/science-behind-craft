import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArtisanContribution,
    CandidateCheck,
    Claim,
    ClaimSource,
    ComponentProposal,
    Concept,
    Craft,
    ImageContribution,
    MediaAsset,
    Source,
    User,
)

from .testimony_seed import rolled_back_session

__all__ = [
    "ADMIN_OWN",
    "AGENT_WAITING",
    "CRAFT",
    "HELD",
    "LIVE",
    "NOW",
    "PICTURE",
    "PROPOSAL",
    "PUBLISHED",
    "RESEARCHED",
    "SLUG",
    "UNGATED",
    "People",
    "TurnsOf",
    "at",
    "seeded_session",
]

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)
SLUG = "Review-Queue-Test-Craft"


def key(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-review-queue/{name}")


CRAFT, CONCEPT, SOURCE, HELD = key("craft"), key("concept"), key("source"), key("held")
AGENT_WAITING, LIVE, RESEARCHED, PUBLISHED = key("agent"), key("live"), key("research"), key("published")
UNGATED, ADMIN_OWN, PROPOSAL, PICTURE = key("ungated"), key("admin-own"), key("proposal"), key("picture")
RESEARCHER, PROFESSOR, ADMIN = key("researcher"), key("professor"), key("admin")


@dataclass(frozen=True)
class People:
    researcher: User
    professor: User
    admin: User


class TurnsOf:
    async def __call__(self, contribution: ArtisanContribution) -> dict[str, dict[str, str]]:
        return {}


def at(minutes: int) -> datetime:
    return NOW - timedelta(minutes=minutes)


async def seeded_session() -> AsyncIterator[tuple[AsyncSession, People]]:
    async for opened in rolled_back_session():
        people = People(
            _person(RESEARCHER, "RESEARCHER", "Meera Contributor"),
            _person(PROFESSOR, "PROFESSOR", "Professor Reviewer"),
            _person(ADMIN, "ADMIN", "Admin Reviewer"),
        )
        opened.add_all([people.researcher, people.professor, people.admin])
        opened.add(Craft(id=CRAFT, slug=SLUG, name="Review Queue Test Craft"))
        opened.add(Source(id=SOURCE, kind="PAPER", title="Indigo vats", licence="CC-BY-4.0", reliability="B"))
        await opened.flush()
        opened.add(Concept(id=CONCEPT, craftId=CRAFT, type="MATERIAL", name="Indigo"))
        await opened.flush()
        await _facts(opened)
        await _proposal(opened)
        await _picture(opened)
        yield opened, people


def _person(user_id: uuid.UUID, role: str, name: str) -> User:
    return User(id=user_id, name=name, email=f"{user_id.hex[:12]}@example.org", role=role)


def _claim(claim_id: uuid.UUID, text: str, **values: object) -> Claim:
    defaults: dict[str, object] = {
        "subjectType": "CONCEPT",
        "subjectId": CONCEPT,
        "predicate": "states",
        "evidenceLevel": "PROVISIONAL",
        "origin": "RESEARCHER",
        "field": "CHEMISTRY",
        "createdById": RESEARCHER,
        "createdByKind": "USER",
    }
    return Claim(id=claim_id, text=text, **(defaults | values))


def _claims() -> list[Claim]:
    return [
        _claim(
            HELD,
            "A reduced indigo vat is yellow-green.",
            origin="IMPORT",
            createdById=None,
            createdAt=at(90),
        ),
        _claim(AGENT_WAITING, "An indigo vat turns blue at its surface.", status="DRAFT", createdAt=at(10)),
        _claim(LIVE, "Lime keeps the indigo vat alkaline.", status="IN_REVIEW", createdAt=at(30)),
        _claim(
            RESEARCHED,
            "Indigo is reduced to leucoindigo in the vat.",
            status="IN_REVIEW",
            origin="LIVE_RESEARCH",
            createdById=None,
            createdByKind="SYSTEM",
            createdAt=at(50),
        ),
        _claim(PUBLISHED, "Indigo is insoluble in water.", status="APPROVED", createdAt=at(70)),
        _claim(UNGATED, "Indigo is a blue dye.", status="DRAFT", createdAt=at(5)),
        _claim(ADMIN_OWN, "Indigo dyeing needs air.", status="DRAFT", createdById=ADMIN, createdAt=at(15)),
    ]


async def _facts(session: AsyncSession) -> None:
    session.add_all(_claims())
    await session.flush()
    for claim_id, found_by in ((AGENT_WAITING, "AGENT"), (LIVE, "CONTRIBUTION"), (RESEARCHED, "ANSWER")):
        session.add(
            ClaimSource(
                claimId=claim_id,
                sourceId=SOURCE,
                quote="the vat is yellow-green",
                locator="p. 4",
                quoteCheck="PASS",
                foundBy=found_by,
            )
        )
    for claim_id in (AGENT_WAITING, LIVE, RESEARCHED, PUBLISHED, ADMIN_OWN):
        session.add_all(_checks(claim_id, [HELD] if claim_id == AGENT_WAITING else []))
    await session.flush()


def _checks(claim_id: uuid.UUID, differs: list[uuid.UUID]) -> list[CandidateCheck]:
    return [
        CandidateCheck(
            claimId=claim_id,
            gate=gate,
            passed=True,
            reasons=[f"{gate.lower()} passed"],
            relatedClaimIds=differs if gate == "DUPLICATE" else [],
            model="judge-model-1" if gate == "NOVELTY" else None,
            checkedAt=NOW,
        )
        for gate in ("NOVELTY", "QUOTES", "DUPLICATE", "SOURCE")
    ]


async def _proposal(session: AsyncSession) -> None:
    session.add(
        ComponentProposal(
            id=PROPOSAL,
            proposerId=RESEARCHER,
            label="review-queue-test-craft/chemistry/vat-surface",
            title="Indigo vat surface",
            description="Shows the blue film forming where the reduced vat meets the air.",
            kind="molecule_3d",
            field="CHEMISTRY",
            craftId=CRAFT,
            subjects=[{"kind": "CRAFT", "key": SLUG}],
            consideredLabels=["shared/chemistry/indigo-reduction"],
            createdAt=at(20),
        )
    )
    await session.flush()


async def _picture(session: AsyncSession) -> None:
    asset = MediaAsset(id=key("asset"), s3Key=f"media/review-queue/{key('asset').hex}.png", mime="image/png")
    session.add(asset)
    await session.flush()
    session.add(
        ImageContribution(
            id=PICTURE,
            contributorId=RESEARCHER,
            craftId=CRAFT,
            claimIds=[HELD],
            origin="PHOTOGRAPH",
            caption="The vat turns yellow-green",
            altText="A clay vat of yellow-green liquid",
            termsVersion="2026-11-19",
            rightsConfirmedAt=NOW,
            status="PENDING",
            assetId=asset.id,
            createdAt=at(40),
        )
    )
    await session.flush()
