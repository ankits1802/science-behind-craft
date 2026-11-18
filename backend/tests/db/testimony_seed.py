import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import (
    AdminDistrict,
    AdminState,
    ArtisanContribution,
    ArtisanConversation,
    ArtisanConversationAudio,
    ArtisanCraft,
    ArtisanProfile,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    Source,
    User,
)

STARTED = datetime(2026, 11, 18, 5, 30, tzinfo=UTC)
QUOTE = "फिटकरी के बाद हम कपड़े को बहते पानी में धोते हैं"
TURN_TEXT = "हाँ। फिटकरी के बाद हम कपड़े को बहते पानी में धोते हैं, फिर धूप में सुखाते हैं।"


@dataclass(frozen=True)
class Seeded:
    artisan: User
    reviewer: User
    craft: Craft
    conversation: ArtisanConversation
    contribution: ArtisanContribution
    fact_claim: uuid.UUID
    turn_id: uuid.UUID


class RecordedObjects:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


async def rolled_back_session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


def _token() -> str:
    return uuid.uuid4().hex[:10]


async def _people(session: AsyncSession) -> tuple[User, User]:
    artisan = User(
        id=uuid.uuid4(), email=f"artisan-{_token()}@example.org", name="Bilal Ismail Khatri", role="ARTISAN"
    )
    reviewer = User(
        id=uuid.uuid4(),
        email=f"prof-{_token()}@example.org",
        name="Reviewer",
        role="PROFESSOR",
        twoFactorEnabled=True,
    )
    session.add_all([artisan, reviewer])
    await session.flush()
    return artisan, reviewer


async def _place(session: AsyncSession) -> tuple[Craft, int]:
    state, district = 990_000 + uuid.uuid4().int % 9_000, 9_900_000 + uuid.uuid4().int % 90_000
    session.add(AdminState(lgd=state, name="Testimony State"))
    await session.flush()
    session.add(AdminDistrict(lgd=district, stateLgd=state, name="Testimony District"))
    craft = Craft(id=uuid.uuid4(), slug=f"Testimony-Print-{_token()}", name="Testimony Print")
    session.add(craft)
    await session.flush()
    return craft, district


async def _fact_claim(session: AsyncSession, craft: Craft) -> uuid.UUID:
    concept = Concept(
        id=uuid.uuid4(), craftId=craft.id, type="PROCESS_STAGE", name="Washing", sensitivity="OPEN"
    )
    source = Source(
        id=uuid.uuid4(), kind="PAPER", title="A study of washing", reliability="B", sensitivity="OPEN"
    )
    session.add_all([concept, source])
    await session.flush()
    claim = Claim(
        id=uuid.uuid4(),
        subjectType="CONCEPT",
        subjectId=concept.id,
        predicate="describes",
        text="Printed cloth is washed in running water after the mordant bath.",
        evidenceLevel="REVIEWED",
        origin="IMPORT",
        status="APPROVED",
        sensitivity="OPEN",
    )
    session.add(claim)
    await session.flush()
    session.add(
        ClaimSource(claimId=claim.id, sourceId=source.id, quote="washed in running water", quoteCheck="PASS")
    )
    await session.flush()
    return claim.id


def _profile(artisan: User, craft: Craft, district: int, credit: str) -> list[object]:
    return [
        ArtisanProfile(
            userId=artisan.id,
            districtLgd=district,
            spokenLanguage="hi",
            creditMode=credit,
            creditName="Bilal Ismail Khatri" if credit == "FULL_NAME" else None,
            creditShortName="Bilal" if credit == "FIRST_NAME" else None,
            adultConfirmedAt=STARTED,
            completedAt=STARTED,
        ),
        ArtisanCraft(userId=artisan.id, craftId=craft.id, position=1),
    ]


def _conversation(artisan: User, craft: Craft) -> ArtisanConversation:
    return ArtisanConversation(
        id=uuid.uuid4(),
        userId=artisan.id,
        craftId=craft.id,
        language="hi",
        transport="RELAY",
        consentVersion="2026-11-18",
        startedAt=STARTED,
        endedAt=STARTED + timedelta(minutes=20),
        transcriptEnc="sealed-transcript",
        extractionStatus="DONE",
        extractionAttempts=1,
        topicsAsked=["PROCESS"],
    )


def _contribution(conversation: ArtisanConversation, turn_id: uuid.UUID) -> ArtisanContribution:
    return ArtisanContribution(
        conversationId=conversation.id,
        userId=conversation.userId,
        craftId=conversation.craftId,
        turnId=turn_id,
        ordinal=3,
        quote=QUOTE,
        quoteLanguage="hi",
        english="After the alum we wash the cloth in running water",
        englishSource="MACHINE",
        claimText="After the alum bath the printed cloth is washed in running water.",
        discipline="PROCESS",
        conceptType="PROCESS_STAGE",
        conceptName="Washing in running water",
        startMs=65_000,
        endMs=72_000,
        locatorPrecision="WORD",
        status="PENDING",
        version=1,
        screens=[],
        corroboratingClaimIds=[],
        createdAt=STARTED + timedelta(minutes=30),
    )


def _audio(conversation: ArtisanConversation, turn_id: uuid.UUID) -> ArtisanConversationAudio:
    return ArtisanConversationAudio(
        conversationId=conversation.id,
        turnId=turn_id,
        ordinal=3,
        objectKey=f"media/{conversation.userId}/{uuid.uuid4().hex}/KalaVigyan_Artisan-Conversation_Recording_T03.webm",
        mimeType="audio/webm",
        bytes=48_000,
        durationMs=12_000,
        startMs=63_000,
    )


async def seed(session: AsyncSession, *, credit: str = "CRAFT_AND_DISTRICT") -> Seeded:
    artisan, reviewer = await _people(session)
    craft, district = await _place(session)
    session.add_all(_profile(artisan, craft, district, credit))
    conversation = _conversation(artisan, craft)
    session.add(conversation)
    await session.flush()
    turn_id = uuid.uuid4()
    contribution = _contribution(conversation, turn_id)
    session.add_all([contribution, _audio(conversation, turn_id)])
    await session.flush()
    fact = await _fact_claim(session, craft)
    return Seeded(artisan, reviewer, craft, conversation, contribution, fact, turn_id)
