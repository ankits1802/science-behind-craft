import uuid
from datetime import UTC, datetime

from app.research.alerts import AnswerImproved, FacetNews
from app.research.explainer import explainer_blocks
from app.retrieval.statements import CraftScope
from app.services.notifications import merged_news
from app.services.saved_recheck import LEVEL_RAISES, NewClaim, SavedCheck, answer_news, claim_facet

from ..contracts.learning_golden import ALERTS, AlertsFixture, learning
from .versions import follow_up_document, latest_golden

CHECKED_AT = datetime(2026, 11, 19, 1, 30, tzinfo=UTC)
CRAFT_ID = uuid.UUID("2f1e0d9c-8b7a-4c6d-9e5f-4a3b2c1d0e9f")


def alerts() -> AlertsFixture:
    return AlertsFixture.model_validate(learning(ALERTS))


def check() -> SavedCheck:
    saved = alerts().saved.items[0]
    latest = follow_up_document(latest_golden()["explainer"]["sections"])
    cited = frozenset(uuid.UUID(c.claim_id) for block in explainer_blocks(latest) for c in block.citations())
    return SavedCheck(
        saved=saved,
        user_id=uuid.UUID(int=7),
        scope=CraftScope(craft_id=CRAFT_ID, sub_category_id=None),
        cited=cited,
        since=datetime(2026, 11, 18, 9, 0, tzinfo=UTC),
    )


def fresh(facet: str | None) -> NewClaim:
    return NewClaim(claim_id=uuid.uuid4(), facet=facet)


def test_a_re_check_with_no_new_claims_makes_no_note() -> None:
    assert answer_news(check(), [], checked_at=CHECKED_AT) is None


def test_a_new_claim_on_a_field_the_reader_did_not_save_makes_no_note() -> None:
    assert answer_news(check(), [fresh("ECONOMICS"), fresh(None)], checked_at=CHECKED_AT) is None


def test_a_claim_the_latest_version_already_cites_is_not_news() -> None:
    cited = next(iter(check().cited))
    assert answer_news(check(), [NewClaim(claim_id=cited, facet="GEOGRAPHY")], checked_at=CHECKED_AT) is None


def test_new_findings_are_counted_per_saved_field_in_the_saved_order() -> None:
    water = [fresh("GEOGRAPHY") for _ in range(3)]
    found = [*water, water[0], fresh("HISTORY"), fresh("ECONOMICS")]
    news = answer_news(check(), found, checked_at=CHECKED_AT)
    assert news == alerts().notifications.items[0].payload


def test_a_claim_counts_for_its_curated_field_first_then_its_concept_s_heading() -> None:
    assert claim_facet("BOTANY", "HISTORICAL_CONTEXT") == "BOTANY"
    assert claim_facet(None, "HISTORICAL_CONTEXT") == "HISTORY"
    assert claim_facet(None, "ENVIRONMENTAL_CONDITION") == "GEOGRAPHY"
    assert claim_facet(None, "SENSORY_CUE") == "PROCESS"
    assert claim_facet(None, "MECHANISM") is None
    assert claim_facet(None, None) is None


def test_a_raise_is_any_move_to_a_stronger_level() -> None:
    assert set(LEVEL_RAISES) == {
        ("REVIEWED", "VERIFIED"),
        ("PROVISIONAL", "VERIFIED"),
        ("PROVISIONAL", "REVIEWED"),
        ("HYPOTHESIS", "VERIFIED"),
        ("HYPOTHESIS", "REVIEWED"),
        ("HYPOTHESIS", "PROVISIONAL"),
    }


def test_an_unread_note_is_replaced_by_one_that_keeps_its_news() -> None:
    earlier = alerts().notifications.items[0].payload
    news = AnswerImproved(
        **{
            **dict(earlier),
            "news": [FacetNews(facet="GEOGRAPHY", new_claims=1), FacetNews(facet="CHEMISTRY", new_claims=2)],
        }
    )
    combined = merged_news(earlier, news)
    assert [(entry.facet, entry.new_claims) for entry in combined.news] == [
        ("GEOGRAPHY", 4),
        ("CHEMISTRY", 2),
        ("HISTORY", 1),
    ]
    newer = news.model_copy(update={"version": 3})
    assert merged_news(earlier, newer) == newer
