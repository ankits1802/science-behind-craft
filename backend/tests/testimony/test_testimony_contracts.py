from typing import Any

from app.schemas.testimony import ContributionsOut, ReviewItemOut
from app.services.testimony_views import contribution_view, review_item

from ..contracts.golden import golden_json, reproduces
from . import fakes

REVIEW_GOLDEN = "testimony.review-item.golden.json"
CONTRIBUTION_GOLDEN = "testimony.contribution.golden.json"


def test_the_review_item_golden_matches_its_response_model() -> None:
    assert reproduces(ReviewItemOut, REVIEW_GOLDEN)


def test_the_contributions_golden_matches_its_response_model() -> None:
    assert reproduces(ContributionsOut, CONTRIBUTION_GOLDEN)


async def test_a_pending_contribution_is_served_to_a_reviewer_as_the_golden() -> None:
    item = fakes.contribution()
    session = fakes.session_for(item, scalars=[fakes.audio()], executed=[fakes.district_row()])
    built = await review_item(session, item, turns=fakes.turns(), links=fakes.FakeLinks(), now=fakes.at(7))
    assert built == golden_json(REVIEW_GOLDEN)


async def test_a_reviewer_sees_no_email_age_or_profile_field() -> None:
    item = fakes.contribution()
    session = fakes.session_for(item, scalars=[fakes.audio()], executed=[fakes.district_row()])
    built: dict[str, Any] = await review_item(session, item, turns=fakes.turns(), links=None, now=fakes.at(7))
    words = str(built).casefold()
    for field in ("email", "ageband", "gender", "spokenlanguage", "creditmode", "adultconfirmed"):
        assert field not in words
    assert built["context"]["audio"] is None


async def test_the_artisan_sees_contributions_as_the_golden() -> None:
    approved = fakes.contribution(
        id=fakes.APPROVED_ID,
        status="APPROVED",
        englishSource="REVIEWED",
        reviewedById=fakes.REVIEWER,
        reviewedAt=fakes.at(9),
        approvedAt=fakes.at(9),
    )
    withdrawn = fakes.contribution(
        id=fakes.WITHDRAWN_ID,
        status="WITHDRAWN",
        quote=None,
        english=None,
        claimText=None,
        withdrawnAt=fakes.at(10, 30),
        textsClearedAt=fakes.at(10, 30),
    )
    session = fakes.session_for(approved, scalars=["PROFESSOR"], executed=[fakes.district_row()])
    items = [await contribution_view(session, approved), await contribution_view(session, withdrawn)]
    counts = {"pending": 1, "approved": 1, "rejected": 0, "withdrawn": 1}
    assert {"counts": counts, "items": items} == golden_json(CONTRIBUTION_GOLDEN)
