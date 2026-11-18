import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.core.guardian_hold import GUARDIAN_CONSENT_REQUIRED_HEADER, GUARDIAN_STATEMENT_VERSION
from app.models import ArtisanContribution, ArtisanProfile, Claim, Concept, ConsentRecord, User
from app.services import craft_process, testimony_store, testimony_writes, what_if_evidence
from app.services.testimony_store import approved_quotes, quote_states
from app.services.testimony_writes import ContributionEdit

from .accounts import bearer, create_user, login, unique_email
from .testimony_seed import TURN_TEXT, Seeded, rolled_back_session, seed

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
NAMED_ENGLISH = "Khatri and I wash the cloth after the alum"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        yield opened


async def approve(
    session: AsyncSession, seeded: Seeded, version: int, reviewer: User | None = None
) -> ArtisanContribution:
    return await testimony_writes.approve(
        session,
        seeded.contribution.id,
        reviewer or seeded.reviewer,
        version=version,
        english_checked=True,
        corroborating_ids=[],
        now=NOW,
    )


async def test_a_reviewer_never_reviews_their_own_words(session: AsyncSession) -> None:
    seeded = await seed(session)
    seeded.artisan.role = "PROFESSOR"
    version = seeded.contribution.version
    with pytest.raises(testimony_store.OwnContribution):
        await approve(session, seeded, version, reviewer=seeded.artisan)
    with pytest.raises(testimony_store.OwnContribution):
        await testimony_writes.reject(
            session,
            seeded.contribution.id,
            seeded.artisan,
            version=version,
            reason="UNCLEAR",
            note=None,
            now=NOW,
        )
    with pytest.raises(testimony_store.OwnContribution):
        await testimony_writes.edit(
            session,
            seeded.contribution.id,
            seeded.artisan,
            change=ContributionEdit(version=version, claim_text="A claim of my own."),
            turn_text=TURN_TEXT,
            now=NOW,
        )
    own_queue = await testimony_store.review_page(session, status="PENDING", reviewer_id=seeded.artisan.id)
    assert seeded.contribution.id not in {row.id for row in own_queue.rows}
    other_queue = await testimony_store.review_page(session, status="PENDING", reviewer_id=seeded.reviewer.id)
    assert seeded.contribution.id in {row.id for row in other_queue.rows}
    assert seeded.contribution.status == "PENDING"


async def test_approval_screens_against_the_current_credit(session: AsyncSession) -> None:
    seeded = await seed(session, credit="FULL_NAME")
    edited = await testimony_writes.edit(
        session,
        seeded.contribution.id,
        seeded.reviewer,
        change=ContributionEdit(version=seeded.contribution.version, english=NAMED_ENGLISH),
        turn_text=TURN_TEXT,
        now=NOW,
    )
    assert edited.screens == []
    profile = await session.get(ArtisanProfile, seeded.artisan.id)
    assert profile is not None
    profile.creditMode = "CRAFT_AND_DISTRICT"
    await session.flush()
    with pytest.raises(testimony_store.ContributionProblems):
        await approve(session, seeded, edited.version)
    assert edited.screens == ["NAME_HELD_BACK"]


async def test_a_credit_change_hides_approved_words_that_name_the_artisan(session: AsyncSession) -> None:
    seeded = await seed(session, credit="FULL_NAME")
    edited = await testimony_writes.edit(
        session,
        seeded.contribution.id,
        seeded.reviewer,
        change=ContributionEdit(version=seeded.contribution.version, english=NAMED_ENGLISH),
        turn_text=TURN_TEXT,
        now=NOW,
    )
    item = await approve(session, seeded, edited.version)
    await session.flush()
    assert [quote.contribution_id for quote in await approved_quotes(session, seeded.craft.id, limit=5)] == [
        seeded.contribution.id
    ]
    profile = await session.get(ArtisanProfile, seeded.artisan.id)
    assert profile is not None
    profile.creditMode = "FIRST_NAME"
    profile.creditShortName = "Bilal"
    assert await testimony_writes.rescreen_contributions(session, seeded.artisan.id) == 1
    await session.flush()
    assert await approved_quotes(session, seeded.craft.id, limit=5) == []
    assert await quote_states(session, [seeded.contribution.id]) == {}
    with pytest.raises(testimony_store.ContributionProblems):
        await approve(session, seeded, item.version)
    fixed = await testimony_writes.edit(
        session,
        seeded.contribution.id,
        seeded.reviewer,
        change=ContributionEdit(version=item.version, english="I wash the cloth after the alum"),
        turn_text=TURN_TEXT,
        now=NOW,
    )
    await session.flush()
    assert fixed.screens == []
    assert len(await approved_quotes(session, seeded.craft.id, limit=5)) == 1


async def test_testimony_rests_on_its_own_concept_never_an_open_one(session: AsyncSession) -> None:
    seeded = await seed(session)
    open_concept = (
        await session.execute(
            select(Concept).where(Concept.craftId == seeded.craft.id, Concept.sensitivity == "OPEN")
        )
    ).scalar_one()
    seeded.contribution.conceptName = open_concept.name
    item = await approve(session, seeded, seeded.contribution.version)
    await session.flush()
    claim = await session.get(Claim, item.claimId)
    assert claim is not None and claim.subjectId != open_concept.id
    testimony_concept = await session.get(Concept, claim.subjectId)
    assert testimony_concept is not None
    assert (testimony_concept.sensitivity, testimony_concept.originRef) == (
        "ATTRIBUTE_REQUIRED",
        "artisan-testimony",
    )
    by_stage = await craft_process._concept_claims(session, [open_concept.id])
    assert claim.id not in {claim_id for ids in by_stage.values() for claim_id in ids}
    by_what_if = await what_if_evidence._concept_claims(session, [open_concept.id])
    assert claim.id not in {claim_id for ids in by_what_if.values() for claim_id in ids}


async def signed_in(client: httpx.AsyncClient, role: str) -> tuple[str, str]:
    email = unique_email(role.lower())
    secret = await create_user(email, role, with_two_factor=role in {"PROFESSOR", "ADMIN"})
    return email, await login(client, email, secret)


async def account_id(email: str) -> str:
    async with session_scope() as opened:
        user = (await opened.execute(select(User).where(User.email == email))).scalar_one()
    return str(user.id)


async def held_student(client: httpx.AsyncClient) -> tuple[str, str, str]:
    email, student = await signed_in(client, "STUDENT")
    saved = await client.put(
        "/api/profile/me/student", json={"ageBand": "UNDER_14", "gender": "UNSAID"}, headers=bearer(student)
    )
    assert saved.status_code == 200, saved.text
    held = await client.get("/api/usage/me", headers=bearer(student))
    assert held.status_code == 403
    assert held.headers[GUARDIAN_CONSENT_REQUIRED_HEADER] == "1"
    assert "parent or guardian" in held.json()["detail"]
    assert (await client.get("/api/auth/me", headers=bearer(student))).status_code == 200
    assert (await client.get("/api/profile/me", headers=bearer(student))).status_code == 200
    return email, await account_id(email), student


async def confirm(client: httpx.AsyncClient, student_id: str, token: str, version: str) -> httpx.Response:
    return await client.post(
        f"/api/users/{student_id}/guardian-consent",
        json={"affirmed": True, "noticeVersion": version},
        headers=bearer(token),
    )


async def test_a_student_under_18_is_held_until_a_professor_confirms(client: httpx.AsyncClient) -> None:
    email, student_id, student = await held_student(client)
    _, professor = await signed_in(client, "PROFESSOR")
    listed = await client.get("/api/users", params={"search": email}, headers=bearer(professor))
    assert [item["guardianConsent"] for item in listed.json()["items"]] == ["NOT_CONFIRMED"]
    stale = await confirm(client, student_id, professor, "2020-01-01")
    confirmed = await confirm(client, student_id, professor, GUARDIAN_STATEMENT_VERSION)
    again = await confirm(client, student_id, professor, GUARDIAN_STATEMENT_VERSION)
    assert (stale.status_code, confirmed.status_code, again.status_code) == (422, 201, 409)
    assert confirmed.json()["userId"] == student_id
    assert (await client.get("/api/usage/me", headers=bearer(student))).status_code == 200
    me = (await client.get("/api/auth/me", headers=bearer(student))).json()
    assert me["guardianConsentRequired"] is False
    async with session_scope() as opened:
        record = (
            await opened.execute(
                select(ConsentRecord).where(
                    ConsentRecord.userId == uuid.UUID(student_id), ConsentRecord.kind == "GUARDIAN_CONSENT"
                )
            )
        ).scalar_one()
    assert record.recordedById is not None and record.noticeVersion == GUARDIAN_STATEMENT_VERSION


async def test_guardian_consent_is_confirmed_only_for_students_and_by_professors(
    client: httpx.AsyncClient,
) -> None:
    researcher_email, researcher = await signed_in(client, "RESEARCHER")
    student_email, _ = await signed_in(client, "STUDENT")
    _, professor = await signed_in(client, "PROFESSOR")
    body = {"affirmed": True, "noticeVersion": GUARDIAN_STATEMENT_VERSION}
    student_id = await account_id(student_email)
    researcher_id = await account_id(researcher_email)
    by_researcher = await client.post(
        f"/api/users/{student_id}/guardian-consent", json=body, headers=bearer(researcher)
    )
    not_student = await client.post(
        f"/api/users/{researcher_id}/guardian-consent", json=body, headers=bearer(professor)
    )
    not_affirmed = await client.post(
        f"/api/users/{student_id}/guardian-consent",
        json={**body, "affirmed": False},
        headers=bearer(professor),
    )
    assert (by_researcher.status_code, not_student.status_code, not_affirmed.status_code) == (403, 404, 422)
    adult = await client.get("/api/users", params={"search": researcher_email}, headers=bearer(professor))
    assert "guardianConsent" not in adult.json()["items"][0]
